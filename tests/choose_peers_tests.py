from django.urls import reverse

from apps.reviews.factories import UserFactory, ReviewFactory
from apps.reviews.models import Review


def test_choose_peers_creates_defaults(running_interval, client):
    manager = UserFactory()
    user = UserFactory(manager=manager)
    subordinates = UserFactory.create_batch(2, manager=user)
    UserFactory(username='otheruser')
    UserFactory(is_active=False, manager=user)
    client.force_login(user=user)
    response = client.get(reverse('users:choose-peers',
                                  kwargs={'interval': running_interval, 'email': user.email}))
    assert response.status_code == 200
    assert {r.reviewer for r in Review.objects.all()} == {manager, subordinates[0], subordinates[1]}


def test_add_peers_success(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user)
    peers = UserFactory.create_batch(4)
    url = reverse('users:choose-peers',
                  kwargs={'interval': running_interval, 'email': user.email})
    client.get(url)
    assert Review.requested.count() == 1  # manager review auto-created
    response = client.post(url, {'peers': [user.manager.id, peers[0].id, peers[1].id]})
    assert {r.reviewer for r in Review.requested.all()} == {user.manager, peers[0], peers[1]}


def test_remove_peers_success(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user)
    ReviewFactory.create_batch(4, target=user, requested=True, interval=running_interval)
    url = reverse('users:choose-peers',
                  kwargs={'interval': running_interval, 'email': user.email})
    client.get(url)
    assert Review.objects.filter(target=user, interval=running_interval).count() == 4
    client.post(url, {'peers': [user.manager.id]})
    assert Review.objects.filter(target=user, interval=running_interval).count() == 1


def test_cant_remove_manager_as_peer(running_interval, client):
    user = UserFactory(with_manager=True)
    client.force_login(user=user)
    manager_review = ReviewFactory(target=user, reviewer=user.manager, requested=True, interval=running_interval)
    ReviewFactory(target=user, requested=True, interval=running_interval)
    other_review = ReviewFactory(target=user, requested=True, interval=running_interval)
    assert Review.objects.filter(target=user, interval=running_interval).count() == 3
    url = reverse('users:choose-peers',
                  kwargs={'interval': running_interval, 'email': user.email})
    client.post(url, {'peers': [other_review.reviewer.id]})
    assert set(Review.objects.filter(target=user, interval=running_interval)) == {manager_review, other_review}


def test_boss_can_choose_peers(running_interval, client):
    boss = UserFactory(manager=None)
    client.force_login(user=boss)
    url = reverse('users:choose-peers',
                  kwargs={'interval': running_interval, 'email': boss.email})
    response = client.get(url)
    assert response.status_code == 200
