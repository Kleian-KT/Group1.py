import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from audit_settings.models import AuditLog, SystemSetting
from audit_settings.forms import SystemSettingsForm
from audit_settings.utils import log_audit
from accounts.permissions import admin_required


@admin_required
def admin_audit_logs(request):
    search_query = request.GET.get('q', '').strip()
    action_filter = request.GET.get('action', '').strip()
    date_filter = request.GET.get('date', '').strip()

    logs_qs = AuditLog.objects.select_related('actor').all().order_by('-timestamp')

    if search_query:
        logs_qs = logs_qs.filter(
            Q(target_reference__icontains=search_query) |
            Q(details__icontains=search_query) |
            Q(actor__username__icontains=search_query)
        )

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)

    if date_filter:
        try:
            parsed_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            logs_qs = logs_qs.filter(timestamp__date=parsed_date)
        except ValueError:
            pass

    paginator = Paginator(logs_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'manage/audit_logs.html', {
        'page_obj': page_obj,
        'actions': AuditLog.ACTION_CHOICES,
        'action_filter': action_filter,
        'search_query': search_query,
        'date_filter': date_filter,
        'active_menu': 'audit'
    })


@admin_required
def admin_settings(request):
    curr_duration = SystemSetting.get_max_duration_hours()
    curr_advance = SystemSetting.get_max_advance_days()

    if request.method == 'POST':
        form = SystemSettingsForm(request.POST)
        if form.is_valid():
            new_duration = form.cleaned_data['max_event_duration_hours']
            new_advance = form.cleaned_data['max_advance_booking_days']

            # Update settings
            s1, _ = SystemSetting.objects.update_or_create(
                key=SystemSetting.MAX_DURATION_KEY,
                defaults={'value': str(new_duration), 'description': 'Maximum event duration in hours'}
            )
            s2, _ = SystemSetting.objects.update_or_create(
                key=SystemSetting.MAX_ADVANCE_WINDOW_KEY,
                defaults={'value': str(new_advance), 'description': 'Maximum advance booking window in days'}
            )

            log_audit(
                request=request,
                action='SETTINGS_UPDATED',
                target_type='SystemSetting',
                target_reference='Booking Limits',
                details=(f"Settings updated by {request.user.username}: "
                         f"Max duration = {new_duration} hrs (was {curr_duration}), "
                         f"Max advance window = {new_advance} days (was {curr_advance})")
            )

            messages.success(request, "System settings have been updated successfully.")
            return redirect('admin_settings')
    else:
        form = SystemSettingsForm(initial={
            'max_event_duration_hours': curr_duration,
            'max_advance_booking_days': curr_advance
        })

    return render(request, 'manage/settings.html', {
        'form': form,
        'curr_duration': curr_duration,
        'curr_advance': curr_advance,
        'active_menu': 'settings'
    })
