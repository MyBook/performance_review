from allauth.exceptions import ImmediateHttpResponse
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.urls import reverse

from apps.users.models import User


class AccountAdapter(DefaultAccountAdapter):
    """Can't register via email"""

    def is_open_for_signup(self, request):
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Can register if email is from SOCIALACCOUNT_DOMAINS_ALLOWED domain or existing user"""

    def is_open_for_signup(self, request, sociallogin):
        return getattr(settings, 'ACCOUNT_ALLOW_REGISTRATION', True)

    def pre_social_login(self, request, sociallogin):
        """Allow to log in via Google automatically.
           We already have existing perf data, so no need for user to connect accounts or confirm ownership.
        """
        if sociallogin.user.pk:
            # Already connected, do nothing
            return
        email = sociallogin.user.email
        if not self.is_allowed_email(email):
            messages.error(request, 'Email %s не разрешён к регистрации, обратитесь в техподдержку' % email)
            raise ImmediateHttpResponse(response=HttpResponseRedirect(reverse('account_login')))

        try:
            user = User.active.get(email=email)
            sociallogin.connect(request, user)
            login(request, user, backend='allauth.account.auth_backends.AuthenticationBackend')
            raise ImmediateHttpResponse(response=HttpResponseRedirect(reverse('users:redirect')))
        except User.DoesNotExist:
            pass

    def is_allowed_email(self, email):
        """Only allow people inside organization to log in
        """
        domain = email.split('@')[-1]
        if domain in settings.SOCIALACCOUNT_DOMAINS_ALLOWED:
            return True

        # make exception for people outside of organization and allow login
        if User.active.filter(email=email).exists():
            return True

        return False
