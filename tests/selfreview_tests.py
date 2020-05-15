import re

import pytest
from django.urls import reverse

from apps.reviews.factories import UserFactory, SelfReviewFactory, IntervalFactory, ReviewFactory
from apps.reviews.models import SelfReview, Review


def test_get_self_review(running_interval, client):
    user = UserFactory()
    old_review = SelfReviewFactory(user=user, published=True,
                                   interval=IntervalFactory(finished=True, name='2017Q4'))
    client.force_login(user=user)
    url = reverse('reviews:create-self-review', kwargs={'interval': running_interval})
    response = client.get(url)
    assert response.context['review_form']
    assert response.context['previous_self_review'] == old_review


@pytest.mark.parametrize(['action', 'redirect_chain'], [
    ('pending', '/2018Q2/users/ygarcia@yahoo.com/'),
    ('draft', '/2018Q2/reviews/self-review/'),
])

def test_post_selfreview_multiple_times(running_interval, client, action, redirect_chain):
    user = UserFactory(with_manager=True, email='ygarcia@yahoo.com')
    client.force_login(user=user)
    url = reverse('reviews:create-self-review', kwargs={'interval': running_interval})
    response = client.post(url, {'text': '123', 'interval': running_interval.id, 'action': action}, follow=True)
    self_review = SelfReview.objects.get(user=user)
    assert self_review.text == '123'
    assert self_review.status == action
    assert redirect_chain in response.redirect_chain[-1][0]

    client.post(url, {'text': '123', 'interval': running_interval.id, 'action': action})
    assert SelfReview.objects.filter(user=user).count() == 1


def test_post_selfreview_rejected_to_pending(running_interval, client):
    self_review = SelfReviewFactory(rejected=True,
                                    interval=running_interval,
                                    user__email='user@example.com',
                                    user__with_manager=True)
    client.force_login(user=self_review.user)
    url = reverse('reviews:self-review', kwargs={'interval': running_interval, 'pk': self_review.id})
    response = client.post(url, {'text': 'xxx', 'interval': running_interval.id, 'action': 'pending'}, follow=True)
    self_review.refresh_from_db()
    assert self_review.text == 'xxx'
    assert self_review.status == SelfReview.STATUS.pending
    assert response.redirect_chain[-1] == ('/2018Q2/users/user@example.com/', 302)


def test_view_self_review_previous_interval(db, client):
    user = UserFactory(first_name='Юзер', last_name='Юзеров')
    client.force_login(user=user)
    self_review_q1 = SelfReviewFactory(user=user, published=True,
                                       interval=IntervalFactory(finished=True, name='2018Q1'))
    self_review_q2 = SelfReviewFactory(user=user, published=True,
                                       interval=IntervalFactory(finished=True, name='2018Q2'))
    IntervalFactory(name='2018Q3', started=True)
    response = client.get(self_review_q2.get_absolute_url())

    response_content = re.sub('[ \n]{2,}', ' ', response.content.decode('utf-8'))
    assert 'Self-review Юзеров Юзер за 2018Q3' not in response_content
    assert 'Self-review Юзеров Юзер за 2018Q2' in response_content
    assert response.context['previous_self_review'] == self_review_q1


def test_approve_selfreview(running_interval, client, mailoutbox):
    self_review = SelfReviewFactory(user__with_manager=True, pending=True,
                                    interval=running_interval,
                                    text='Это мой селф-ревью')
    peer_review = ReviewFactory(target=self_review.user, requested=True, interval=running_interval)
    other_target_review = ReviewFactory(requested=True, interval=running_interval)
    client.force_login(user=self_review.user.manager)
    mailoutbox.clear()
    response = client.post(self_review.get_absolute_url(), {'action': 'published'})

    self_review.refresh_from_db()
    assert self_review.status == SelfReview.STATUS.published
    peer_review.refresh_from_db()
    assert peer_review.status == Review.STATUS.draft
    assert mailoutbox[0].to[0] == peer_review.reviewer.email
    assert 'Прошу тебя оценить' in mailoutbox[0].subject
    assert self_review.text in mailoutbox[0].message().as_string()

    other_target_review.refresh_from_db()
    assert other_target_review.status == Review.STATUS.requested


def test_cant_approve_own_selfreview(running_interval, client):
    self_review = SelfReviewFactory(user__with_manager=True, pending=True)
    client.force_login(user=self_review.user)
    response = client.post(self_review.get_absolute_url(), {'action': 'published'})
    assert response.context['approve_form'].errors['__all__'].as_data()[0].code == 'not_manager'
    self_review.refresh_from_db()
    assert self_review.status == SelfReview.STATUS.pending


def test_boss_review_is_approved_instantly(running_interval, client):
    boss = UserFactory(manager=None)
    client.force_login(user=boss)
    url = reverse('reviews:create-self-review', kwargs={'interval': running_interval})
    client.post(url, {'text': '123', 'interval': running_interval.id, 'action': 'pending'}, follow=True)
    self_review = SelfReview.objects.get(user=boss)
    assert self_review.text == '123'
    assert self_review.status == SelfReview.STATUS.published
