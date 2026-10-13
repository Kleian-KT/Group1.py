from django.urls import path
from reservations import views as res_views
from facilities import views as fac_views
from accounts import views as acc_views
from events import views as ev_views
from reporting import views as rep_views
from audit_settings import views as aud_views

urlpatterns = [
    # Dashboard
    path('', res_views.admin_dashboard, name='admin_dashboard'),
    
    # User Management (A1)
    path('users/', acc_views.admin_user_list, name='admin_user_list'),
    path('users/<int:user_id>/', acc_views.admin_user_detail, name='admin_user_detail'),
    path('users/<int:user_id>/toggle-status/', acc_views.admin_user_toggle_status, name='admin_user_toggle_status'),
    
    # Facility, Category, Amenity Management (A2)
    path('facilities/', fac_views.admin_facility_list, name='admin_facility_list'),
    path('facilities/create/', fac_views.admin_facility_create, name='admin_facility_create'),
    path('facilities/<int:facility_id>/', fac_views.admin_facility_detail, name='admin_facility_detail'),
    path('facilities/<int:facility_id>/edit/', fac_views.admin_facility_edit, name='admin_facility_edit'),
    path('facilities/<int:facility_id>/archive/', fac_views.admin_facility_archive, name='admin_facility_archive'),
    path('facilities/<int:facility_id>/operating-hours/', fac_views.admin_facility_save_operating_hour, name='admin_facility_save_operating_hour'),
    path('facilities/<int:facility_id>/amenity/add/', fac_views.admin_facility_add_amenity, name='admin_facility_add_amenity'),
    path('facilities/<int:facility_id>/amenity/<int:amenity_id>/remove/', fac_views.admin_facility_remove_amenity, name='admin_facility_remove_amenity'),
    path('categories/', fac_views.admin_category_list, name='admin_category_list'),
    path('categories/<int:category_id>/archive/', fac_views.admin_category_archive, name='admin_category_archive'),
    path('amenities/', fac_views.admin_amenity_list, name='admin_amenity_list'),
    path('amenities/<int:amenity_id>/archive/', fac_views.admin_amenity_archive, name='admin_amenity_archive'),
    
    # Reservation Review, Reschedule, Cancellation (A3 & A4)
    path('reservations/', res_views.admin_reservation_list, name='admin_reservation_list'),
    path('reservations/<int:reservation_id>/', res_views.admin_reservation_detail, name='admin_reservation_detail'),
    path('reservations/<int:reservation_id>/approve/', res_views.admin_reservation_approve, name='admin_reservation_approve'),
    path('reservations/<int:reservation_id>/reject/', res_views.admin_reservation_reject, name='admin_reservation_reject'),
    path('reservations/<int:reservation_id>/reschedule/', res_views.admin_reservation_reschedule, name='admin_reservation_reschedule'),
    path('reservations/<int:reservation_id>/cancel/', res_views.admin_reservation_cancel, name='admin_reservation_cancel'),
    
    # Calendar (A4)
    path('calendar/', res_views.admin_calendar, name='admin_calendar'),
    
    # Event Monitoring (A5)
    path('events/', ev_views.admin_event_list, name='admin_event_list'),
    path('events/<int:reservation_id>/check-in/', ev_views.admin_event_check_in, name='admin_event_check_in'),
    path('events/<int:reservation_id>/complete/', ev_views.admin_event_complete, name='admin_event_complete'),
    path('events/<int:reservation_id>/no-show/', ev_views.admin_event_no_show, name='admin_event_no_show'),
    path('events/<int:reservation_id>/print/', ev_views.admin_event_print_slip, name='admin_event_print_slip'),
    
    # Closures (A6)
    path('closures/', res_views.admin_closure_list, name='admin_closure_list'),
    path('closures/<int:closure_id>/archive/', res_views.admin_closure_archive, name='admin_closure_archive'),
    
    # Reports & Analytics (A7)
    path('reports/', rep_views.admin_reports, name='admin_reports'),
    path('reports/export/', rep_views.admin_reports_export_csv, name='admin_reports_export_csv'),
    
    # Audit Logs (A8)
    path('audit/', aud_views.admin_audit_logs, name='admin_audit_logs'),
    
    # System Settings (A8)
    path('settings/', aud_views.admin_settings, name='admin_settings'),
]
