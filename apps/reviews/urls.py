from django.urls import path

from . import views

app_name = 'reviews'
urlpatterns = [
    path('self-review/create/', view=views.CreateSelfReview.as_view(), name='create-self-review'),
    path('self-review/<int:pk>/', view=views.EditSelfReview.as_view(), name='self-review'),
    path('add-reviews/', view=views.AddReviews.as_view(), name='add-reviews'),
    path('approve-reviews/', view=views.ApproveReviews.as_view(), name='approve-reviews'),
    path('<int:pk>/', view=views.ReviewDetail.as_view(), name='reviews-detail'),
]
