from django.urls import path
from reservations import views as res_views
from facilities import views as fac_views
from accounts import views as acc_views

urlpatterns = [
    path('', res_views.user_dashboard, name='user_dashboard'),
    path('profile/', acc_views.profile_view, name='user_profile'),
    
    # Facilities discovery
    path('facilities/', fac_views.user_facility_list, name='user_facility_list'),
    path('facilities/<int:facility_id>/', fac_views.user_facility_detail, name='user_facility_detail'),
    
    # Reservations management
    path('reservations/', res_views.user_reservation_list, name='user_reservation_list'),
    path('reservations/create/', res_views.user_reservation_create, name='user_reservation_create'),
    path('reservations/<int:reservation_id>/', res_views.user_reservation_detail, name='user_reservation_detail'),
    path('reservations/<int:reservation_id>/cancel/', res_views.user_reservation_cancel, name='user_reservation_cancel'),
    
    # Real-time Availability API
    path('api/availability/', res_views.api_facility_availability, name='api_facility_availability'),
]
