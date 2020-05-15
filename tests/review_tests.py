import pytest
from django.urls import reverse

from apps.reviews.factories import ReviewFactory, SelfReviewFactory, UserFactory, IntervalFactory
from apps.reviews.models import SelfReview, Review


@pytest.mark.parametrize(['status', 'visitor_slug', 'can_see'], [
    (Review.STATUS.draft, 'target', False),
    (Review.STATUS.draft, 'manager', True),
    (Review.STATUS.draft, 'reviewer', True),
    (Review.STATUS.draft, 'other_user', False),
])
def test_review_detail_visibility(running_interval, client, status, visitor_slug, can_see):
    review = ReviewFactory(interval=running_interval,
                           target__with_manager=True,
                           status=status)
    SelfReviewFactory(user=review.target, interval=running_interval, published=True)
    users = {
        'target': review.target,
        'manager': review.target.manager,
        'reviewer': review.reviewer,
        'other_user': UserFactory(),
        'superuser': UserFactory(is_superuser=True)
    }
    client.force_login(user=users[visitor_slug])
    response = client.get(review.get_absolute_url())
    if can_see:
        assert response.status_code == 200
        assert response.context['object'] == review
    else:
        assert response.status_code == 403


def test_review_previous_review_visibility(running_interval, client):
    ancient_interval = IntervalFactory(name='2018Q3')
    old_interval = IntervalFactory(name='2018Q4')
    previous_interval = IntervalFactory(name='2019Q1')
    review = ReviewFactory(interval=running_interval,
                           target__with_manager=True,
                           draft=True)
    SelfReviewFactory(user=review.target, interval=running_interval, published=True)
    client.force_login(user=review.reviewer)

    response = client.get(review.get_absolute_url())
    assert not response.context['previous_review']

    honeypot_not_mine_review = ReviewFactory(interval=previous_interval, target=review.target,
                                             published=True)
    previous_review = ReviewFactory(interval=old_interval, target=review.target,
                                    reviewer=review.reviewer, published=True)
    ancient_review = ReviewFactory(interval=ancient_interval, target=review.target,
                                   reviewer=review.reviewer, published=True)

    response = client.get(review.get_absolute_url())
    assert response.context['previous_review'] == previous_review


def test_cant_view_review_if_no_self_review(running_interval, client):
    review = ReviewFactory(interval=running_interval,
                           target__with_manager=True)
    client.force_login(user=review.target.manager)
    assert not SelfReview.objects.exists()
    response = client.get(review.get_absolute_url())
    assert response.status_code == 403


def test_cant_view_review_if_self_review_not_published(running_interval, client):
    review = ReviewFactory(interval=running_interval,
                           target__with_manager=True)
    SelfReviewFactory(user=review.target, interval=running_interval, draft=True)
    client.force_login(user=review.target.manager)
    response = client.get(review.get_absolute_url())
    assert response.status_code == 403


def test_can_review_if_self_review_is_published(running_interval, client):
    review = ReviewFactory(interval=running_interval,
                           target__with_manager=True)
    SelfReviewFactory(user=review.target, interval=running_interval, published=True)
    client.force_login(user=review.target.manager)
    response = client.get(review.get_absolute_url())
    assert response.status_code == 200


def test_shown_only_reviews_with_published_selfreview(running_interval, client):
    reviewer = UserFactory()
    review_with_approved_selfreview = ReviewFactory(interval=running_interval, reviewer=reviewer)
    review_with_draft_selfreview = ReviewFactory(interval=running_interval, reviewer=reviewer)

    # not shown
    published_review = ReviewFactory(interval=running_interval, reviewer=reviewer, published=True)
    hidden_review = ReviewFactory(interval=running_interval, reviewer=reviewer, hidden=True)
    SelfReviewFactory(user=published_review.target, interval=running_interval, published=True)
    SelfReviewFactory(user=hidden_review.target, interval=running_interval, published=True)

    SelfReviewFactory(user=review_with_approved_selfreview.target, interval=running_interval, published=True)
    SelfReviewFactory(user=review_with_draft_selfreview.target, interval=running_interval, draft=True)
    client.force_login(user=reviewer)

    response = client.get(reverse('reviews:add-reviews', kwargs={'interval': running_interval}))
    assert response.status_code == 200
    assert list(response.context['current_reviews']) == [review_with_approved_selfreview]

    response = client.get(reviewer.get_absolute_url(interval=running_interval))
    assert response.status_code == 200
    assert list(response.context['draft_reviews']) == [review_with_approved_selfreview]


@pytest.mark.parametrize(['action', 'visitor_slug', 'expected_status'], [
    (Review.STATUS.draft, 'manager', Review.STATUS.draft),
    (Review.STATUS.pending, 'manager', Review.STATUS.hidden),
    (Review.STATUS.draft, 'other_user', Review.STATUS.draft),
    (Review.STATUS.pending, 'other_user', Review.STATUS.pending),
])
def test_submit_review(running_interval, client, action, visitor_slug, expected_status):
    user = UserFactory(with_manager=True)
    users = {
        'manager': user.manager,
        'other_user': UserFactory(),
    }
    review = ReviewFactory(interval=running_interval, target=user, reviewer=users[visitor_slug], draft=True)
    SelfReviewFactory(user=user, interval=running_interval, published=True)
    client.force_login(user=users[visitor_slug])
    response = client.post(review.get_absolute_url(), {
        'score': 1,
        'text': 'some text',
        'interval': running_interval.id,
        'action': action
    }, follow=True)
    assert response.status_code == 200
    review.refresh_from_db()
    assert review.status == expected_status


def test_no_review_score_in_email_templates():
    from os import listdir
    from os.path import isfile, join
    email_tmeplates_dir = 'perf/templates/email'
    templates_list = [join(email_tmeplates_dir, f)
                      for f in listdir(email_tmeplates_dir)
                      if isfile(join(email_tmeplates_dir, f))]
    assert len(templates_list)
    assert 'review.score' not in ''.join((open(f).read() for f in templates_list))
