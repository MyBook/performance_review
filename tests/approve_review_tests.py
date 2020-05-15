from django.urls import reverse

from apps.reviews.factories import UserFactory, ReviewFactory, SelfReviewFactory


def test_approve_reviews_requires_login(running_interval, client):
    response = client.get(reverse('reviews:approve-reviews', kwargs={'interval': running_interval}),
                          follow=True)
    url, status = response.redirect_chain[0]
    assert url.startswith('/accounts/login/?')
    assert status == 302


def test_approve_reviews_context(running_interval, client):
    target_user = UserFactory(with_manager=True)
    review_published = ReviewFactory(target=target_user, interval=running_interval, published=True)
    review_hidden = ReviewFactory(target=target_user, interval=running_interval, hidden=True)
    review_pending = ReviewFactory(target=target_user, interval=running_interval, pending=True)
    review_draft = ReviewFactory(target=target_user, interval=running_interval, draft=True)

    SelfReviewFactory(user=target_user, interval=running_interval, published=True)
    client.force_login(user=target_user.manager)

    response = client.get(reverse('reviews:approve-reviews', kwargs={'interval': running_interval}))
    assert set(response.context['reviews_require_approval']) == {review_pending}
    assert set(response.context['reviews_approved']) == {review_published, review_hidden}


def test_approve_review_by_manager_success(running_interval, client):
    self_review = SelfReviewFactory(user__with_manager=True, interval=running_interval, published=True)
    review = ReviewFactory(target=self_review.user, interval=running_interval, pending=True)
    client.force_login(user=review.target.manager)
    client.post(review.get_absolute_url(), {'action': 'hidden'})
    review.refresh_from_db()
    assert review.status == review.STATUS.hidden


def test_cant_approve_own_review(running_interval, client):
    self_review = SelfReviewFactory(user__with_manager=True, interval=running_interval, published=True)
    review = ReviewFactory(target=self_review.user, interval=running_interval, pending=True)
    client.force_login(user=review.reviewer)
    response = client.post(review.get_absolute_url(), {'action': 'hidden'})
    assert response.context['approve_form'].errors['__all__'].as_data()[0].code == 'not_manager'
    review.refresh_from_db()
    assert review.status == review.STATUS.pending
