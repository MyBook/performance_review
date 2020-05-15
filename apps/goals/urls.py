from django.urls import path

from . import views

app_name = 'goals'
urlpatterns = [
    path('<email>/create/', view=views.CreateGoal.as_view(), name='create'),
    path('<int:pk>/', view=views.EditGoal.as_view(), name='detail'),
]
