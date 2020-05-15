import re
from unittest import mock

import pytest
import responses
from allauth.socialaccount.models import SocialAccount
from django.core.management import call_command
from django.urls import reverse

from apps.goals.factories import GoalFactory
from apps.reviews.factories import UserFactory, SelfReviewFactory, ReviewFactory
from apps.users.models import User
from apps.users.signals import fetch_avatar


def test_anon_home(running_interval, client):
    response = client.get(reverse('home'), follow=True)
    assert response.redirect_chain[-1] == ('/accounts/login/?next=/', 302)


def test_logged_user_redirected_to_profile(running_interval, client):
    user = UserFactory()
    client.force_login(user=user)
    response = client.get(reverse('home'), follow=True)
    assert response.resolver_match.view_name == 'users:detail'


def test_list_users(running_interval, client):
    user = UserFactory()
    client.force_login(user=user)
    response = client.get(reverse('users:list', kwargs={'interval': running_interval}))
    assert list(response.context['user_list']) == [user]


def test_user_detail_subordinate_stats_not_visible_to_peers(running_interval, client):
    user = UserFactory(with_manager=True)
    colleague = UserFactory()
    client.force_login(user=colleague)
    response = client.get(user.manager.get_absolute_url())
    assert list(response.context['subordinates']) == [user]
    assert not hasattr(response.context['subordinates'][0], 'self_review')
    assert not hasattr(response.context['subordinates'][0], 'peers_approved')
    assert not hasattr(response.context['subordinates'][0], 'peers_require_approval')
    assert not hasattr(response.context['subordinates'][0], 'peers_draft')
    assert not hasattr(response.context['subordinates'][0], 'current_written_reviews')
    assert not hasattr(response.context['subordinates'][0], 'current_reviews')


def test_user_detail_inactive_subordinates(running_interval, client):
    user = UserFactory(with_manager=True)
    disabled_user = UserFactory(manager=user.manager, is_active=False)
    client.force_login(user=user.manager)
    response = client.get(user.manager.get_absolute_url())
    assert list(response.context['subordinates']) == [user]


@pytest.mark.parametrize(['login_as_user', 'is_visible'], [
    ('user', True),
    ('manager', True),
    ('other_user', False),
    ('superuser', True),
])
def test_user_detail_goal_is_visible(running_interval, next_interval, client, login_as_user, is_visible):
    users = {
        'user': UserFactory(with_manager=True),
        'other_user': UserFactory(),
        'superuser': UserFactory(is_superuser=True),
    }
    users['manager'] = users['user'].manager
    current_goal = GoalFactory(target=users['user'],
                               interval=running_interval)
    next_goal = GoalFactory(target=users['user'],
                            interval=next_interval)

    client.force_login(user=users[login_as_user])
    response = client.get(users['user'].get_absolute_url())
    if is_visible:
        assert response.context['current_goal'] == current_goal
        assert response.context['next_goal'] == next_goal
    else:
        assert not response.context.get('current_goal')
        assert not response.context.get('next_goal')


def test_user_disabled_visible_in_admin(db, client):
    disabled_user = UserFactory(is_active=False)
    client.force_login(user=UserFactory(is_superuser=True, is_staff=True))
    response = client.get(reverse('admin:users_user_change', args=[disabled_user.id]))
    assert response.status_code == 200
    assert response.context['original'] == disabled_user


def test_user_detail_inactive_peers(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user)
    active_review = ReviewFactory(interval=running_interval, target=user, reviewer__is_active=True)
    inactive_review = ReviewFactory(interval=running_interval, target=user, reviewer__is_active=False)
    response = client.get(user.manager.get_absolute_url())
    assert list(response.context['current_peers']) == [active_review.reviewer]


def test_get_absolute_url_inactive_user(running_interval):
    disabled_user = UserFactory(is_active=False)
    assert not disabled_user.get_absolute_url()


def test_user_detail_subordinate_stats_visible_to_superuser(running_interval, admin_client):
    user = UserFactory(with_manager=True)
    self_review = SelfReviewFactory(interval=running_interval, user=user, published=True)
    user_to_manager_review = ReviewFactory(interval=running_interval, target=user.manager, reviewer=user, draft=True)
    manager_to_user_review = ReviewFactory(interval=running_interval, target=user, reviewer=user.manager, draft=True)
    finished_to_user_review = ReviewFactory(interval=running_interval, target=user, hidden=True)
    rejected_to_user_review = ReviewFactory(interval=running_interval, target=user, rejected=True)
    pending_subordinate_review = ReviewFactory(interval=running_interval, reviewer=user, pending=True)
    requested_subordinate_review = ReviewFactory(interval=running_interval, reviewer=user, requested=True)
    hidden_subordinate_review = ReviewFactory(interval=running_interval, reviewer=user, hidden=True)
    published_subordinate_review = ReviewFactory(interval=running_interval, reviewer=user, published=True)

    response = admin_client.get(user.manager.get_absolute_url())
    assert list(response.context['subordinates']) == [user]
    assert response.context['subordinates'][0].self_review == self_review
    assert list(response.context['subordinates'][0].peers_approved) == [finished_to_user_review.reviewer]
    assert list(response.context['subordinates'][0].peers_require_approval) == [rejected_to_user_review.reviewer]
    assert list(response.context['subordinates'][0].peers_draft) == [manager_to_user_review.reviewer]
    assert set(response.context['subordinates'][0].current_written_reviews) == {pending_subordinate_review,
                                                                                hidden_subordinate_review,
                                                                                published_subordinate_review}
    assert set(response.context['subordinates'][0].current_reviews) == {user_to_manager_review,
                                                                        pending_subordinate_review,
                                                                        requested_subordinate_review,
                                                                        hidden_subordinate_review,
                                                                        published_subordinate_review}


def test_user_detail_reviews_context(running_interval, client):
    user = UserFactory(with_manager=True)
    draft = ReviewFactory(interval=running_interval, reviewer=user, draft=True)
    pending = ReviewFactory(interval=running_interval, reviewer=user, pending=True)
    approved = ReviewFactory(interval=running_interval, reviewer=user, hidden=True)
    rejected = ReviewFactory(interval=running_interval, reviewer=user, rejected=True)
    # make sure everyone has selfreview
    [SelfReviewFactory(interval=running_interval, user=u, published=True) for u in User.objects.all()]

    client.force_login(user=user)
    response = client.get(user.get_absolute_url())
    assert list(response.context['draft_reviews']) == [draft]
    assert list(response.context['pending_reviews']) == [pending]
    assert list(response.context['approved_reviews']) == [approved]
    assert list(response.context['rejected_reviews']) == [rejected]


@pytest.mark.parametrize(['visitor_slug', 'can_see'], [
    ('manager', True),
    ('user', False),
    ('other_user', False),
    ('superuser', True),
])
def test_manager_can_see_subordinate_summary_url(visitor_slug, can_see, running_interval, client):
    user = UserFactory(with_manager=True)
    users = {
        'user': user,
        'manager': user.manager,
        'other_user': UserFactory(),
        'superuser': UserFactory(is_superuser=True)
    }
    client.force_login(user=users[visitor_slug])
    response = client.get(user.get_absolute_url())
    assert bool(response.context.get('summary_url')) == can_see


def test_user_cant_see_own_summary(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user)
    response = client.get(reverse('users:summary', kwargs={'interval': running_interval, 'email': user.email}))
    assert response.status_code == 403


def test_reviewer_cant_see_other_guy_summary(running_interval, client):
    user = UserFactory(with_manager=True)
    other = UserFactory()
    ReviewFactory(interval=running_interval, target=user, reviewer=other, published=True)
    client.force_login(user=other)
    response = client.get(reverse('users:summary', kwargs={'interval': running_interval, 'email': user.email}))
    assert response.status_code == 403


def test_manager_can_see_subordinate_summary(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user.manager)
    review = ReviewFactory(interval=running_interval, target=user, reviewer=UserFactory(), published=True)
    other_review = ReviewFactory(interval=running_interval, target=UserFactory(), reviewer=user.manager, published=True)
    response = client.get(reverse('users:summary', kwargs={'interval': running_interval, 'email': user.email}))
    assert response.status_code == 200
    assert list(response.context['reviews']) == [review]


def test_manager_review_is_first_one(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user.manager)
    review_by_manager = ReviewFactory(interval=running_interval, target=user, reviewer=user.manager, published=True)
    review_by_peer = ReviewFactory(interval=running_interval, target=user, reviewer=UserFactory(), published=True)
    response = client.get(reverse('users:summary', kwargs={'interval': running_interval, 'email': user.email}))
    assert list(response.context['reviews']) == [review_by_manager, review_by_peer]


@responses.activate
@mock.patch('django.core.files.storage.FileSystemStorage.save')
def test_fetch_avatar_does_not_overwrite_in_aws(mock_save, db, settings):
    responses.add(responses.GET, re.compile(r'http://1x1px\.me/.+'),
                  body=open('tests/fixtures/1x1.png', 'rb').read())
    mock_save.side_effect = lambda name, *args, **kwargs: name  # identity save

    user1, user2 = UserFactory(), UserFactory()
    account1 = SocialAccount(provider='google', user=user1, uid='1',
                             extra_data={'picture': 'http://1x1px.me/yszgHjRfq24/photo.jpg'})
    account2 = SocialAccount(provider='google', user=user1, uid='1',
                             extra_data={'picture': 'http://1x1px.me/sLbe8rOXpaQ/photo.jpg'})

    fetch_avatar(request=None, user=user1, account=account1)
    fetch_avatar(request=None, user=user2, account=account2)

    user1.refresh_from_db()
    user2.refresh_from_db()
    assert user1.avatar
    assert user1.avatar != user2.avatar


def test_tree(db, capsys):
    boss = UserFactory(last_name='Boss', job__name='CEO')
    UserFactory(last_name='Dilbert', job__name='программист', manager=boss)
    boss2 = UserFactory(first_name='Jen', last_name='Barber', job__name='манагер')
    UserFactory(first_name='Moris', last_name='Moss', job__name='эникейщик', manager=boss2, is_reviewable=False)
    call_command('tree')
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        'Barber Jen (манагер)',
        ' +-- [X] Moss Moris (эникейщик)',
        'Boss (CEO)',
        ' +-- Dilbert (программист)',
    ]
