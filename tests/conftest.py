from urllib.parse import urlparse, parse_qs

import pytest
from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialApp
from allauth.tests import MockedResponse, mocked_response
from django.contrib.sites.models import Site
from django.urls import reverse

from apps.reviews.factories import IntervalFactory


@pytest.fixture
def finished_interval(db):
    return IntervalFactory(name='2018Q1', finished=True)


@pytest.fixture
def running_interval(db):
    return IntervalFactory(name='2018Q2', started=True)


@pytest.fixture
def next_interval(db):
    return IntervalFactory(name='2018Q3', pending=True)


@pytest.fixture
def social_app(db):
    site = Site.objects.get_current()
    for provider in providers.registry.get_list():
        app = SocialApp.objects.create(
            provider=provider.id,
            name=provider.id,
            client_id='app123id',
            key='123',
            secret='dummy')
        app.sites.add(site)


@pytest.fixture
def social_login(social_app, client):
    def _social_login(**google_params):
        with mocked_response(MockedResponse(200, 'oauth_token=token&oauth_token_secret=psst',
                                            {'content-type': 'text/html'})):
            resp = client.get(reverse('google_login'), dict(process='login'))

        p = urlparse(resp['location'])
        q = parse_qs(p.query)
        complete_url = reverse('google_callback')
        assert q['redirect_uri'][0].find(complete_url) > 0
        response_json = get_login_response_json()
        with mocked_response(
            MockedResponse(200, response_json, {'content-type': 'application/json'}),
                get_mocked_response(**google_params)):
            response = client.get(complete_url, {'code': 'test', 'state': q['state'][0]}, follow=True)
        return response
    return _social_login


def get_login_response_json(with_refresh_token=True):
    rt = ''
    if with_refresh_token:
        rt = ',"refresh_token": "testrf"'
    return """{
        "uid":"weibo",
        "access_token":"testac"
        %s }""" % rt


def get_mocked_response(family_name='Penners',
                        given_name='Raymond',
                        name='Raymond Penners',
                        email="raymond.penners@example.com",
                        verified_email=True):
    return MockedResponse(200, """
              {"family_name": "%s", "name": "%s",
               "picture": "https://lh5.googleusercontent.com/photo.jpg",
               "locale": "nl", "gender": "male",
               "email": "%s",
               "link": "https://plus.google.com/108204268033311374519",
               "given_name": "%s", "id": "108204268033311374519",
               "verified_email": %s }
        """ % (family_name,
               name,
               email,
               given_name,
               (repr(verified_email).lower())))
