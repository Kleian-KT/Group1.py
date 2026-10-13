from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError

from reservations.models import Reservation
from events.models import EventRecord
from events.forms import EventCheckInForm, EventCompletionForm, EventNoShowForm
from reservations.services import (
    check_in_event, complete_event, mark_event_no_show,
    ReservationWorkflowError
)
from accounts.permissions import admin_required


@admin_required
def admin_event_list(request):
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()
    facility_id = request.GET.get('facility', '').strip()

    # Focus on reservations that require or have operational handling
    events_qs = Reservation.objects.filter(
        status__in=[
            Reservation.STATUS_APPROVED,
            Reservation.STATUS_CHECKED_IN,
            Reservation.STATUS_COMPLETED,
            Reservation.STATUS_NO_SHOW
        ]
    ).select_related('facility', 'user', 'event_record').order_by('-start_time')

    if status_filter:
        events_qs = events_qs.filter(status=status_filter)

    if facility_id:
        events_qs = events_qs.filter(facility_id=facility_id)

    if search_query:
        events_qs = events_qs.filter(
            Q(reference__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(facility__name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    paginator = Paginator(events_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'manage/event_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'facility_id': facility_id,
        'now': timezone.now(),
        'active_menu': 'events'
    })


@admin_required
@require_POST
def admin_event_check_in(request, reservation_id):
    form = EventCheckInForm(request.POST)
    actual_start = None
    if form.is_valid():
        actual_start = form.cleaned_data.get('actual_start_time')

    try:
        check_in_event(reservation_id, request.user, actual_start_time=actual_start, request=request)
        messages.success(request, "Event successfully checked in! The facility is now in active use.")
    except (ReservationWorkflowError, ValidationError) as e:
        messages.error(request, f"Check-in failed: {e}")

    return redirect('admin_event_list')


@admin_required
@require_POST
def admin_event_complete(request, reservation_id):
    form = EventCompletionForm(request.POST)
    if form.is_valid():
        actual_end = form.cleaned_data.get('actual_end_time')
        completion_notes = form.cleaned_data.get('completion_notes', '')
        incident_notes = form.cleaned_data.get('incident_notes', '')

        try:
            complete_event(
                reservation_id=reservation_id,
                admin_user=request.user,
                actual_end_time=actual_end,
                incident_notes=incident_notes,
                completion_notes=completion_notes,
                request=request
            )
            messages.success(request, "Event marked as Completed! Operational notes saved.")
        except (ReservationWorkflowError, ValidationError) as e:
            messages.error(request, f"Completion failed: {e}")
    else:
        messages.error(request, "Invalid completion details submitted.")

    return redirect('admin_event_list')


@admin_required
@require_POST
def admin_event_no_show(request, reservation_id):
    form = EventNoShowForm(request.POST)
    no_show_notes = ""
    if form.is_valid():
        no_show_notes = form.cleaned_data.get('no_show_notes', '')

    try:
        mark_event_no_show(
            reservation_id=reservation_id,
            admin_user=request.user,
            no_show_notes=no_show_notes,
            request=request
        )
        messages.warning(request, "Event recorded as No Show.")
    except (ReservationWorkflowError, ValidationError) as e:
        messages.error(request, f"Operation failed: {e}")

    return redirect('admin_event_list')


@admin_required
def admin_event_print_slip(request, reservation_id):
    reservation = get_object_or_404(
        Reservation.objects.select_related('facility', 'user', 'decision_by'),
        id=reservation_id
    )
    event_record = getattr(reservation, 'event_record', None)

    return render(request, 'manage/event_print_slip.html', {
        'reservation': reservation,
        'event_record': event_record,
        'now': timezone.now()
    })
