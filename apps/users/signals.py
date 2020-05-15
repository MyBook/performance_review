import logging
from urllib.parse import urlparse

import requests
from allauth.account.signals import user_logged_in
from django.core.files.base import ContentFile
from django.dispatch import receiver
from django.template.defaultfilters import slugify

logger = logging.getLogger(__name__)


def name_from_url(url):
    p = urlparse(url)
    for base in (p.path.split('/')[-1],
                 p.path,
                 p.netloc):
        name = ".".join(filter(lambda s: s,
                               map(slugify, base.split("."))))
        if name:
            return name


def fetch_avatar(request, user, account):
    """
    Download user avatar from social network
    """
    url = account.get_avatar_url()
    if not url:
        logger.debug('No avatar for user %s', user.id)
        return
    try:
        image_content = requests.get(url, timeout=5).content
        image = ContentFile(image_content)
        filename = '{email}_{orig_name}'.format(
            email=user.email.replace('@', '_'),
            orig_name=name_from_url(url)
        )
        user.avatar.save(filename, image)
        user.save(update_fields=['avatar'])
        logger.info('Updated avatar %s for user %s', filename, user.id)
    except IOError:
        logger.error('Failed to update avatar', exc_info=True)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, response, user, **kwargs):
    sociallogin = kwargs.get('sociallogin')
    if sociallogin and not user.avatar:
        fetch_avatar(request=request,
                     user=sociallogin.account.user,
                     account=sociallogin.account)
