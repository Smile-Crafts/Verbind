from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.TripListView.as_view(), name='trip-list'),
    path('post/', views.TripCreateView.as_view(), name='trip-create'),
    path('my-rides/', views.my_trips, name='my-trips'),
    path('trip/<int:pk>/', views.trip_detail, name='trip-detail'),
    path('trip/<int:pk>/edit/', views.TripUpdateView.as_view(), name='trip-edit'),
    path('trip/<int:pk>/delete/', views.trip_delete, name='trip-delete'),
    path('trip/<int:pk>/join/', views.request_to_join, name='trip-join'),
    path('trip/<int:pk>/leave/', views.leave_trip, name='trip-leave'),
    path('trip/<int:pk>/chat/<int:user_id>/', views.trip_chat, name='trip-chat'),
    path('trip/<int:pk>/status/<str:new_status>/', views.set_trip_status, name='trip-status'),
    path('trip/<int:pk>/rate/<int:user_id>/', views.rate_participant, name='trip-rate'),

    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('profile/', views.edit_profile, name='edit-profile'),
    path('verify/', views.verify_identity, name='verify-identity'),
    path('verify-email/resend/', views.resend_verification_email, name='resend-verification-email'),
    path('verify-email/<str:token>/', views.verify_email, name='verify-email'),
    path('get-verified/', views.verification_gate, name='verification-gate'),

    path('drivers/', TemplateView.as_view(template_name='trips/drivers_coming_soon.html'), name='drivers'),
    path('verai/', TemplateView.as_view(template_name='trips/verai_coming_soon.html'), name='verai'),

    path('messages/', views.messages_inbox, name='messages-inbox'),
    path('api/check-username/', views.check_username, name='check-username'),
    path('api/location-search/', views.location_search, name='location-search'),
]
