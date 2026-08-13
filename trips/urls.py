from django.urls import path
from . import views

urlpatterns = [
    path('', views.TripListView.as_view(), name='trip-list'),
    path('post/', views.TripCreateView.as_view(), name='trip-create'),
    path('trip/<int:pk>/', views.trip_detail, name='trip-detail'),
    path('trip/<int:pk>/join/', views.request_to_join, name='trip-join'),
    path('trip/<int:pk>/status/<str:new_status>/', views.set_trip_status, name='trip-status'),
    path('trip/<int:pk>/rate/<int:user_id>/', views.rate_participant, name='trip-rate'),

    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('profile/', views.edit_profile, name='edit-profile'),
    path('verify/', views.verify_identity, name='verify-identity'),
]
