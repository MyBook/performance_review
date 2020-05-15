from django.conf import settings
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.reviews.factories import UserFactory
from apps.users.models import User


def test_login_page(db, client):
    response = client.get(reverse('account_login'))
    assert 'Google' in response.content.decode('utf-8')


def test_google_login_alien(running_interval, social_login, client):
    response = social_login(email='raymond.penners@example.com')
    assert (str(list(get_messages(response.wsgi_request))[0]) ==
            'Email raymond.penners@example.com не разрешён к регистрации, обратитесь в техподдержку')
    assert User.objects.count() == 0


def test_google_login_allowed_domain(settings, running_interval, social_login, client):
    settings.SOCIALACCOUNT_DOMAINS_ALLOWED = ['example.com', 'foo.bar']
    response = social_login(email='user@example.com')
    assert response.status_code == 200
    assert response.redirect_chain[-1] == ('/2018Q2/users/user@example.com/', 302)
    user = User.objects.get()
    assert user.email == 'user@example.com'
    assert user.is_active


def test_google_login_existing(running_interval, social_login, client):
    settings.SOCIALACCOUNT_DOMAINS_ALLOWED = []
    UserFactory(email='raymond.penners@example.com')
    assert 'example.com' not in settings.SOCIALACCOUNT_DOMAINS_ALLOWED
    response = social_login(email='raymond.penners@example.com')
    assert response.status_code == 200
    assert response.redirect_chain[-1] == ('/2018Q2/users/raymond.penners@example.com/', 302)
    user = User.objects.get()
    assert user.email == 'raymond.penners@example.com'
    assert user.is_active
