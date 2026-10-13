from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect


class ActiveUserEnforcementMiddleware:
    """
    Ensures that deactivated users cannot perform transactions or stay logged in,
    even if their session has not expired.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
            messages.error(request, "Your account has been deactivated. Please contact an administrator.")
            return redirect('login')
        return self.get_response(request)
