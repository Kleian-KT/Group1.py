from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST

from accounts.forms import UserRegistrationForm, UserProfileForm, AdminUserUpdateForm
from accounts.permissions import admin_required, active_user_required
from audit_settings.utils import log_audit
from reservations.models import Reservation

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account '{user.username}' created successfully! You can now sign in.")
            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, "Your account has been deactivated. Please contact an administrator.")
                return render(request, 'accounts/login.html', {'form': form})
            
            login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            return redirect('login_redirect')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been successfully signed out.")
    return redirect('login')


def login_redirect_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_admin_role():
        return redirect('admin_dashboard')
    return redirect('user_dashboard')


@active_user_required
def profile_view(request):
    """Basic user profile view and edit."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=request.user)

    user_reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')[:5]

    return render(request, 'portal/profile.html', {
        'form': form,
        'user_reservations': user_reservations,
        'active_menu': 'profile'
    })


# -------------------------------------------------------------
# A1 — Admin User Management Views
# -------------------------------------------------------------

@admin_required
def admin_user_list(request):
    search_query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    users_qs = User.objects.all().order_by('-date_joined')

    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(student_or_employee_id__icontains=search_query)
        )

    if role_filter:
        users_qs = users_qs.filter(role=role_filter)

    if status_filter == 'active':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(is_active=False)

    paginator = Paginator(users_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'manage/user_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'active_menu': 'users'
    })


@admin_required
def admin_user_detail(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    reservations = Reservation.objects.filter(user=target_user).select_related('facility').order_by('-created_at')

    res_paginator = Paginator(reservations, 10)
    res_page_number = request.GET.get('page')
    res_page_obj = res_paginator.get_page(res_page_number)

    return render(request, 'manage/user_detail.html', {
        'target_user': target_user,
        'res_page_obj': res_page_obj,
        'active_menu': 'users'
    })


@admin_required
@require_POST
def admin_user_toggle_status(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "Security violation: Administrators cannot deactivate their own active account.")
        return redirect('admin_user_detail', user_id=target_user.id)

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    action_label = "ACCOUNT_ACTIVATED" if target_user.is_active else "ACCOUNT_DEACTIVATED"
    status_str = "activated" if target_user.is_active else "deactivated"

    log_audit(
        request=request,
        action=action_label,
        target_type='User',
        target_id=str(target_user.id),
        target_reference=target_user.username,
        details=f"User {target_user.username} was {status_str} by administrator {request.user.username}"
    )

    messages.success(request, f"Account '{target_user.username}' has been {status_str}.")
    return redirect('admin_user_detail', user_id=target_user.id)
