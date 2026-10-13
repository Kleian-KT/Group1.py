"""
URL configuration for Campus Facility Reservation Management System.
"""
from django.urls import path, include
from django.shortcuts import redirect


def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_admin_role():
        return redirect('admin_dashboard')
    return redirect('user_dashboard')


urlpatterns = [
    path('', root_redirect, name='root'),
    path('', include('accounts.urls')),
    path('portal/', include('reservations.user_urls')),
    path('manage/', include('reservations.admin_urls')),
]
