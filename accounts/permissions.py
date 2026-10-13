from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_active or not request.user.is_admin_role():
            messages.error(request, "Access restricted. Administrator privileges required.")
            raise PermissionDenied("Administrator privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def active_user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_active:
            messages.error(request, "Your account has been deactivated.")
            raise PermissionDenied("Account deactivated.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
