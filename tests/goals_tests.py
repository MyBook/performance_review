import pytest
from django.urls import reverse

from apps.goals.factories import GoalFactory
from apps.goals.models import Goal
from apps.reviews.factories import UserFactory, IntervalFactory


def test_manager_can_get_goal_createform(running_interval, client):
    user = UserFactory(with_manager=True)
    old_goal = GoalFactory(target=user,
                           interval=IntervalFactory(finished=True, name='2017Q4'))

    url = reverse('goals:create', kwargs={'interval': running_interval, 'email': user.email})
    client.force_login(user=user.manager)
    response = client.get(url)
    assert response.context['goal_form']
    assert response.context['previous_goal'] == old_goal


@pytest.mark.parametrize(['login_as_user'], [
    ('user',),
    ('other_user',),
])
def test_only_manager_can_create_goals(running_interval, client, login_as_user):
    users = {
        'user': UserFactory(with_manager=True),
        'other_user': UserFactory(),
    }
    url = reverse('goals:create', kwargs={'interval': running_interval, 'email': users['user'].email})
    client.force_login(user=users[login_as_user])
    response = client.get(url)
    assert response.status_code == 403
    assert not response.context

    response = client.post(url, {'text': '123', 'interval': running_interval.id}, follow=True)
    assert response.status_code == 403
    assert Goal.objects.count() == 0


def test_manager_can_create_goal(running_interval, client):
    user = UserFactory(with_manager=True, email='ygarcia@yahoo.com')
    client.force_login(user=user.manager)
    url = reverse('goals:create', kwargs={'interval': running_interval, 'email': user.email})
    response = client.post(url, {'text': '123', 'interval': running_interval.id}, follow=True)
    goal = Goal.objects.get(target=user)
    assert goal.text == '123'
    assert goal.interval == running_interval
    assert '/2018Q2/users/ygarcia@yahoo.com/' in response.redirect_chain[-1][0]


def test_manager_can_view_and_update_goal(running_interval, client):
    user = UserFactory(with_manager=True, email='ygarcia@yahoo.com')
    current_goal = GoalFactory(target=user,
                               text='456',
                               interval=running_interval)
    client.force_login(user=user.manager)
    response = client.get(current_goal.get_absolute_url())
    assert response.context['goal_form']['text'].value() == '456'

    response = client.post(current_goal.get_absolute_url(),
                           {'text': '123', 'interval': running_interval.id}, follow=True)
    goal = Goal.objects.get(target=user)
    assert goal.text == '123'
    assert goal.interval == running_interval
    assert '/2018Q2/users/ygarcia@yahoo.com/' in response.redirect_chain[-1][0]


@pytest.mark.parametrize(['login_as_user'], [
    ('user',),
    ('other_user',),
    ('superuser',),
])
def test_only_manager_can_update_goal(running_interval, client, login_as_user):
    users = {
        'user': UserFactory(with_manager=True),
        'other_user': UserFactory(),
        'superuser': UserFactory(is_superuser=True),
    }
    current_goal = GoalFactory(target=users['user'],
                               text='456',
                               interval=running_interval)
    client.force_login(user=users[login_as_user])
    response = client.post(current_goal.get_absolute_url(),
                           {'text': '123', 'interval': running_interval.id}, follow=True)
    assert response.status_code == 403


@pytest.mark.parametrize(['login_as_user', 'status_code'], [
    ('user', 200),
    ('other_user', 403),
    ('superuser', 200),
])
def test_user_can_see_hers_goal(running_interval, client, login_as_user, status_code):
    users = {
        'user': UserFactory(with_manager=True),
        'other_user': UserFactory(),
        'superuser': UserFactory(is_superuser=True),
    }
    current_goal = GoalFactory(target=users['user'],
                               text='456',
                               interval=running_interval)
    client.force_login(user=users[login_as_user])
    response = client.get(current_goal.get_absolute_url())
    assert response.status_code == status_code
