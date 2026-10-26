import datetime
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.http import JsonResponse

from facilities.models import Facility, FacilityCategory
from reservations.models import Reservation, ClosureBlock, ReservationChange
from reservations.forms import (
    ReservationSubmissionForm, ReservationRejectForm, 
    ReservationRescheduleForm, ReservationAdminCancelForm, ClosureBlockForm
)
from reservations.services import (
    submit_reservation, approve_reservation, reject_reservation,
    reschedule_approved_reservation, cancel_reservation_by_user,
    cancel_reservation_by_admin, create_closure_block, archive_closure_block,
    get_overlapping_approved_reservations, get_overlapping_closures,
    validate_reservation_times_and_rules, ReservationConflictError, ReservationWorkflowError,
    calculate_facility_slots
)
from audit_settings.models import SystemSetting
from accounts.permissions import admin_required, active_user_required


# -------------------------------------------------------------
# Section 6 — Custom Admin Dashboard (/manage/)
# -------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    now = timezone.now()

    # 4 Real Database KPI metrics
    pending_count = Reservation.objects.filter(status=Reservation.STATUS_PENDING).count()
    approved_upcoming_count = Reservation.objects.filter(
        status=Reservation.STATUS_APPROVED,
        start_time__gte=now
    ).count()
    completed_count = Reservation.objects.filter(status=Reservation.STATUS_COMPLETED).count()
    active_facilities_count = Facility.objects.filter(is_active=True).count()

    # Recent Pending Requests queue (limit 5)
    recent_pending = Reservation.objects.filter(
        status=Reservation.STATUS_PENDING
    ).select_related('facility', 'user').order_by('-created_at')[:5]

    # Chart 1: Monthly Reservation Volume (calculated from database)
    monthly_labels = []
    monthly_counts = []
    # Generate past 6 months
    for i in range(5, -1, -1):
        # Calculate month range
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = datetime.date(year, month, 1).strftime('%b %Y')
        monthly_labels.append(label)

        # Count reservations created in this month
        count = Reservation.objects.filter(
            start_time__year=year,
            start_time__month=month
        ).count()
        monthly_counts.append(count)

    # Chart 2: Facility Usage Comparison (total bookings per active facility)
    facility_usage = Facility.objects.filter(is_active=True).annotate(
        booking_count=Count('reservations')
    ).order_by('-booking_count')[:6]

    facility_labels = [f.code for f in facility_usage]
    facility_counts = [f.booking_count for f in facility_usage]

    return render(request, 'manage/dashboard.html', {
        'pending_count': pending_count,
        'approved_upcoming_count': approved_upcoming_count,
        'completed_count': completed_count,
        'active_facilities_count': active_facilities_count,
        'recent_pending': recent_pending,
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_counts_json': json.dumps(monthly_counts),
        'facility_labels_json': json.dumps(facility_labels),
        'facility_counts_json': json.dumps(facility_counts),
        'active_menu': 'dashboard'
    })


# -------------------------------------------------------------
# Section 9 — A3: Reservation Review & Approval Queue
# -------------------------------------------------------------

@admin_required
def admin_reservation_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    facility_id = request.GET.get('facility', '').strip()
    date_filter = request.GET.get('date', '').strip()

    reservations_qs = Reservation.objects.select_related('facility', 'user').order_by('-created_at')

    if search_query:
        reservations_qs = reservations_qs.filter(
            Q(reference__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    if status_filter:
        reservations_qs = reservations_qs.filter(status=status_filter)

    if facility_id:
        reservations_qs = reservations_qs.filter(facility_id=facility_id)

    if date_filter:
        try:
            parsed_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            reservations_qs = reservations_qs.filter(start_time__date=parsed_date)
        except ValueError:
            pass

    facilities = Facility.objects.all().order_by('name')

    paginator = Paginator(reservations_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'manage/reservation_list.html', {
        'page_obj': page_obj,
        'facilities': facilities,
        'statuses': Reservation.STATUS_CHOICES,
        'search_query': search_query,
        'status_filter': status_filter,
        'facility_id': facility_id,
        'date_filter': date_filter,
        'active_menu': 'reservations'
    })


@admin_required
def admin_reservation_detail(request, reservation_id):
    reservation = get_object_or_404(
        Reservation.objects.select_related('facility', 'user', 'decision_by'),
        id=reservation_id
    )

    # Contextual validation preview
    facility = reservation.facility
    booking_date = reservation.start_time.date()
    is_closed, open_time, close_time = facility.get_operating_hours_for_date(booking_date)

    # Active closures on that day
    closures = ClosureBlock.objects.filter(
        facility=facility,
        is_active=True,
        start_time__date=booking_date
    )

    # Approved bookings on that day
    approved_same_day = Reservation.objects.filter(
        facility=facility,
        status__in=[Reservation.STATUS_APPROVED, Reservation.STATUS_CHECKED_IN],
        start_time__date=booking_date
    ).exclude(id=reservation.id)

    # Validation errors preview if pending
    validation_warnings = []
    if reservation.status == Reservation.STATUS_PENDING:
        validation_warnings = validate_reservation_times_and_rules(
            facility=facility,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            participant_count=reservation.participant_count,
            is_submission=False
        )

    # Reschedule history
    change_history = reservation.changes.select_related('changed_by').all()

    reject_form = ReservationRejectForm()
    cancel_form = ReservationAdminCancelForm()

    return render(request, 'manage/reservation_detail.html', {
        'reservation': reservation,
        'facility': facility,
        'is_closed': is_closed,
        'open_time': open_time,
        'close_time': close_time,
        'closures': closures,
        'approved_same_day': approved_same_day,
        'validation_warnings': validation_warnings,
        'change_history': change_history,
        'reject_form': reject_form,
        'cancel_form': cancel_form,
        'active_menu': 'reservations'
    })


@admin_required
@require_POST
def admin_reservation_approve(request, reservation_id):
    try:
        approve_reservation(reservation_id, request.user, request=request)
        messages.success(request, "Reservation successfully approved!")
    except ReservationConflictError as e:
        messages.error(request, f"Approval Conflict: {e}")
    except (ReservationWorkflowError, ValidationError) as e:
        messages.error(request, f"Approval Failed: {e}")
    except Exception as e:
        messages.error(request, f"Unexpected error during approval: {e}")

    return redirect('admin_reservation_detail', reservation_id=reservation_id)


@admin_required
@require_POST
def admin_reservation_reject(request, reservation_id):
    form = ReservationRejectForm(request.POST)
    if form.is_valid():
        reason = form.cleaned_data['reason']
        try:
            reject_reservation(reservation_id, request.user, reason, request=request)
            messages.success(request, "Reservation has been rejected.")
        except Exception as e:
            messages.error(request, f"Rejection failed: {e}")
    else:
        messages.error(request, "A reason is mandatory when rejecting a reservation.")

    return redirect('admin_reservation_detail', reservation_id=reservation_id)


@admin_required
def admin_reservation_reschedule(request, reservation_id):
    reservation = get_object_or_404(
        Reservation.objects.select_related('facility'),
        id=reservation_id
    )

    if reservation.status != Reservation.STATUS_APPROVED:
        messages.error(request, "Only Approved reservations may be rescheduled.")
        return redirect('admin_reservation_detail', reservation_id=reservation.id)

    if request.method == 'POST':
        form = ReservationRescheduleForm(request.POST)
        if form.is_valid():
            new_start = form.cleaned_data['new_start_time']
            new_end = form.cleaned_data['new_end_time']
            reason = form.cleaned_data['reason']

            try:
                reschedule_approved_reservation(
                    reservation_id=reservation.id,
                    new_start_time=new_start,
                    new_end_time=new_end,
                    reason=reason,
                    admin_user=request.user,
                    request=request
                )
                messages.success(request, "Reservation rescheduled successfully.")
                return redirect('admin_reservation_detail', reservation_id=reservation.id)
            except (ReservationConflictError, ReservationWorkflowError, ValidationError) as e:
                messages.error(request, f"Reschedule failed: {e}")
    else:
        form = ReservationRescheduleForm(initial={
            'new_start_time': reservation.start_time.strftime('%Y-%m-%dT%H:%M'),
            'new_end_time': reservation.end_time.strftime('%Y-%m-%dT%H:%M'),
        })

    return render(request, 'manage/reservation_reschedule.html', {
        'reservation': reservation,
        'form': form,
        'active_menu': 'reservations'
    })


@admin_required
@require_POST
def admin_reservation_cancel(request, reservation_id):
    form = ReservationAdminCancelForm(request.POST)
    if form.is_valid():
        reason = form.cleaned_data['reason']
        try:
            cancel_reservation_by_admin(reservation_id, request.user, reason, request=request)
            messages.success(request, "Reservation cancelled successfully by administrator.")
        except Exception as e:
            messages.error(request, f"Cancellation failed: {e}")
    else:
        messages.error(request, "Cancellation reason is required.")

    return redirect('admin_reservation_detail', reservation_id=reservation_id)


# -------------------------------------------------------------
# Section 10 — A4: Calendar and Schedule (/manage/calendar/)
# -------------------------------------------------------------

@admin_required
def admin_calendar(request):
    view_type = request.GET.get('view', 'week').strip() # 'day' or 'week'
    facility_id = request.GET.get('facility', '').strip()
    date_str = request.GET.get('date', '').strip()

    now = timezone.now()
    if date_str:
        try:
            curr_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            curr_date = now.date()
    else:
        curr_date = now.date()

    if view_type == 'day':
        start_date = curr_date
        end_date = curr_date
        prev_date = (curr_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        next_date = (curr_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        period_title = curr_date.strftime('%A, %B %d, %Y')
    else:
        # Week view: starting Monday of the current week
        start_date = curr_date - datetime.timedelta(days=curr_date.weekday())
        end_date = start_date + datetime.timedelta(days=6)
        prev_date = (start_date - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        next_date = (start_date + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        period_title = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"

    # Build date list
    date_days = []
    tmp = start_date
    while tmp <= end_date:
        date_days.append(tmp)
        tmp += datetime.timedelta(days=1)

    start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))

    reservations_qs = Reservation.objects.filter(
        start_time__lte=end_dt,
        end_time__gte=start_dt
    ).select_related('facility', 'user').order_by('start_time')

    closures_qs = ClosureBlock.objects.filter(
        is_active=True,
        start_time__lte=end_dt,
        end_time__gte=start_dt
    ).select_related('facility').order_by('start_time')

    if facility_id:
        reservations_qs = reservations_qs.filter(facility_id=facility_id)
        closures_qs = closures_qs.filter(facility_id=facility_id)

    facilities = Facility.objects.all().order_by('name')

    return render(request, 'manage/calendar.html', {
        'view_type': view_type,
        'curr_date': curr_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'period_title': period_title,
        'date_days': date_days,
        'reservations': reservations_qs,
        'closures': closures_qs,
        'facilities': facilities,
        'facility_id': facility_id,
        'today': now.date(),
        'active_menu': 'calendar'
    })


# -------------------------------------------------------------
# Section 12 — A6: Closure and Availability Management
# -------------------------------------------------------------

@admin_required
def admin_closure_list(request):
    closures = ClosureBlock.objects.select_related('facility', 'created_by').all().order_by('-start_time')
    facilities = Facility.objects.filter(is_active=True).order_by('name')

    conflicts = []
    form = ClosureBlockForm()

    if request.method == 'POST':
        form = ClosureBlockForm(request.POST)
        if form.is_valid():
            fac = form.cleaned_data['facility']
            st = form.cleaned_data['start_time']
            et = form.cleaned_data['end_time']
            reason = form.cleaned_data['reason']

            try:
                create_closure_block(fac, st, et, reason, request.user, request=request)
                messages.success(request, f"Closure period created for {fac.name}.")
                return redirect('admin_closure_list')
            except ReservationConflictError as e:
                messages.error(request, str(e))
                conflicts = e.conflicts
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please correct the errors in the closure form.")

    return render(request, 'manage/closure_list.html', {
        'closures': closures,
        'facilities': facilities,
        'form': form,
        'conflicts': conflicts,
        'active_menu': 'closures'
    })


@admin_required
@require_POST
def admin_closure_archive(request, closure_id):
    try:
        archive_closure_block(closure_id, request.user, request=request)
        messages.success(request, "Closure block archived successfully.")
    except Exception as e:
        messages.error(request, f"Error archiving closure: {e}")
    return redirect('admin_closure_list')


# -------------------------------------------------------------
# Basic User Portal Views (/portal/)
# -------------------------------------------------------------

@active_user_required
def user_dashboard(request):
    now = timezone.now()
    user = request.user

    my_pending = Reservation.objects.filter(user=user, status=Reservation.STATUS_PENDING).count()
    my_approved_upcoming = Reservation.objects.filter(
        user=user, status=Reservation.STATUS_APPROVED, start_time__gte=now
    ).count()
    my_total = Reservation.objects.filter(user=user).count()

    recent_reservations = Reservation.objects.filter(
        user=user
    ).select_related('facility').order_by('-created_at')[:6]

    featured_facilities = Facility.objects.filter(is_active=True).order_by('?')[:3]

    return render(request, 'portal/dashboard.html', {
        'my_pending': my_pending,
        'my_approved_upcoming': my_approved_upcoming,
        'my_total': my_total,
        'recent_reservations': recent_reservations,
        'featured_facilities': featured_facilities,
        'active_menu': 'dashboard'
    })


@active_user_required
def user_reservation_list(request):
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()

    qs = Reservation.objects.filter(user=request.user).select_related('facility').order_by('-created_at')

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search_query:
        qs = qs.filter(
            Q(reference__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(facility__name__icontains=search_query)
        )

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'portal/reservation_list.html', {
        'page_obj': page_obj,
        'statuses': Reservation.STATUS_CHOICES,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_menu': 'reservations'
    })


@active_user_required
def user_reservation_create(request):
    initial_facility = request.GET.get('facility')
    initial_date = request.GET.get('date')
    initial_start = request.GET.get('start') or request.GET.get('start_time')
    initial_end = request.GET.get('end') or request.GET.get('end_time')

    if request.method == 'POST':
        form = ReservationSubmissionForm(request.POST)
        if form.is_valid():
            try:
                res = submit_reservation(
                    user=request.user,
                    facility=form.cleaned_data['facility'],
                    title=form.cleaned_data['title'],
                    purpose=form.cleaned_data['purpose'],
                    participant_count=form.cleaned_data['participant_count'],
                    start_time=form.cleaned_data['start_time'],
                    end_time=form.cleaned_data['end_time'],
                    request=request
                )
                messages.success(
                    request,
                    f"Reservation request submitted successfully! Your tracking reference is {res.reference}."
                )
                return redirect('user_reservation_detail', reservation_id=res.id)
            except ValidationError as e:
                for err in e.messages if hasattr(e, 'messages') else [str(e)]:
                    messages.error(request, err)
    else:
        initial = {}
        if initial_facility:
            initial['facility'] = initial_facility
        if initial_date:
            st = initial_start[:5] if initial_start else "09:00"
            et = initial_end[:5] if initial_end else "10:00"
            initial['start_time'] = f"{initial_date}T{st}"
            initial['end_time'] = f"{initial_date}T{et}"
        form = ReservationSubmissionForm(initial=initial)

    max_duration = SystemSetting.get_max_duration_hours()
    max_advance = SystemSetting.get_max_advance_days()
    today = timezone.now().date()
    max_date = today + datetime.timedelta(days=max_advance)
    default_date = initial_date or (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    return render(request, 'portal/reservation_create.html', {
        'form': form,
        'max_duration': max_duration,
        'max_advance': max_advance,
        'today_str': today.strftime('%Y-%m-%d'),
        'max_date_str': max_date.strftime('%Y-%m-%d'),
        'default_date': default_date,
        'preset_start': initial_start[:5] if initial_start else '',
        'preset_end': initial_end[:5] if initial_end else '',
        'active_menu': 'reservations'
    })


@active_user_required
def user_reservation_detail(request, reservation_id):
    # Strictly scoped to logged-in user
    reservation = get_object_or_404(
        Reservation.objects.select_related('facility', 'user'),
        id=reservation_id,
        user=request.user
    )

    can_cancel = reservation.can_be_cancelled_by_user()
    change_history = reservation.changes.all()

    return render(request, 'portal/reservation_detail.html', {
        'reservation': reservation,
        'can_cancel': can_cancel,
        'change_history': change_history,
        'active_menu': 'reservations'
    })


@active_user_required
@require_POST
def user_reservation_cancel(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    try:
        cancel_reservation_by_user(reservation.id, request.user, request=request)
        messages.success(request, "Your reservation request has been cancelled.")
    except Exception as e:
        messages.error(request, f"Cancellation failed: {e}")
    return redirect('user_reservation_detail', reservation_id=reservation.id)


@active_user_required
def api_facility_availability(request):
    """
    Returns real-time hourly slot availability for a facility on a specific date.
    All non-available slots (pending holds, approved bookings, closures, past time)
    are strictly labeled 'Unavailable' with no applicant or status details disclosed.
    """
    facility_id = request.GET.get('facility_id')
    date_str = request.GET.get('date')

    if not facility_id:
        return JsonResponse({'error': 'Facility ID is required.'}, status=400)

    try:
        facility = Facility.objects.select_related('category').get(id=facility_id)
    except (Facility.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Facility not found.'}, status=404)

    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format (expected YYYY-MM-DD).'}, status=400)
    else:
        target_date = timezone.now().date()

    availability_data = calculate_facility_slots(facility, target_date)
    open_t = availability_data.get('open_time')
    close_t = availability_data.get('close_time')
    open_disp = availability_data.get('open_time_display') or (facility.default_open_time.strftime('%I:%M %p').lstrip('0') if facility.default_open_time else '')
    close_disp = availability_data.get('close_time_display') or (facility.default_close_time.strftime('%I:%M %p').lstrip('0') if facility.default_close_time else '')
    op_hours_display = f"{open_disp} - {close_disp}" if open_disp and close_disp else "8:00 AM - 8:00 PM"

    facility_info = {
        'id': facility.id,
        'name': facility.name,
        'code': facility.code,
        'location': facility.location,
        'capacity': facility.capacity,
        'category': facility.category.name if facility.category else '',
        'image_url': facility.get_image_url(),
        'badge_color': facility.badge_color,
        'operating_hours': op_hours_display,
        'is_active': facility.is_active,
    }

    return JsonResponse({
        'facility': facility_info,
        'date': target_date.strftime('%Y-%m-%d'),
        'display_date': target_date.strftime('%A, %B %d, %Y'),
        'is_closed': availability_data.get('is_closed', False),
        'open_time': open_t,
        'close_time': close_t,
        'open_time_display': open_disp,
        'close_time_display': close_disp,
        'slots': availability_data.get('slots', []),
        'max_duration': SystemSetting.get_max_duration_hours(),
        'max_advance': SystemSetting.get_max_advance_days()
    })

