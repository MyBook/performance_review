from django.urls import path

from apps.reviews.views import ChoosePeers
from . import views

app_name = 'users'
urlpatterns = [
    path('users/~redirect/', view=views.UserRedirectView.as_view(), name='redirect'),
    path('<slug:interval>/users/', view=views.UserListView.as_view(), name='list'),
    path('<slug:interval>/users/<email>/', view=views.UserDetailView.as_view(), name='detail',),
    path('<slug:interval>/users/<email>/summary/', view=views.SummaryView.as_view(), name='summary',),
    path('<slug:interval>/users/<email>/peers/', view=ChoosePeers.as_view(), name='choose-peers'),
]
