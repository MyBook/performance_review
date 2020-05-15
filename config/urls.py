from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views import defaults as default_views
from django.views.generic import TemplateView

from apps.reviews.views import ChoosePeers
from apps.users.views import UserRedirectView

urlpatterns = [
    url(r'^$', UserRedirectView.as_view(), name='home'),
    url(r'^about/$', login_required(TemplateView.as_view(template_name='pages/about.html')), name='about',),
    url(settings.ADMIN_URL, admin.site.urls),
    url(r'', include('apps.users.urls', namespace='users'), ),
    url(r'^(?P<interval>\w+)/', include([
        url(r'^reviews/', include('apps.reviews.urls', namespace='reviews'), ),
        url(r'^goals/', include('apps.goals.urls', namespace='goals'), ),
    ])),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^hijack/', include('hijack.urls', namespace='hijack')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += [
        url(r'^400/$', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')},),
        url(r'^403/$', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')},),
        url(r'^404/$', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')},),
        url(r'^500/$', default_views.server_error),
    ]
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [url(r'^__debug__/', include(debug_toolbar.urls))] + urlpatterns
