from django.conf import settings
from django.contrib.sites.models import Site

from apps.reviews.models import Interval


def last_interval(request):
    try:
        return {
            'last_interval': Interval.active.latest()
        }
    except Interval.DoesNotExist:
        return {}


def site(request):
    try:
        return {
            'domain': Site.objects.get_current().domain
        }
    except Site.DoesNotExist:
        return {}


def content(request):
    """Custom urls"""
    return {
        'CONTENT_FREE_FEEDBACK_URL': settings.CONTENT_FREE_FEEDBACK_URL,
        'CONTENT_DESCRIPTION_PAGE': settings.CONTENT_DESCRIPTION_PAGE,
        'CONTENT_TIPS_PAGE': settings.CONTENT_TIPS_PAGE,
        'CONTENT_SUPPORT_EMAIL': settings.CONTENT_SUPPORT_EMAIL,
        'CONTENT_EMAIL_SIGNATURE': settings.CONTENT_EMAIL_SIGNATURE,
        'CONTENT_SELFREVIEW_EXAMPLE': settings.CONTENT_SELFREVIEW_EXAMPLE,
    }
