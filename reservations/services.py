import datetime
import threading
from django.db import transaction, OperationalError, DatabaseError
from django.utils import timezone
from django.core.exceptions import ValidationError

_approval_concurrency_lock = threading.Lock()

from facilities.models import Facility
from reservations.models import Reservation, ClosureBlock, ReservationChange
from events.models import EventRecord
from audit_settings.models import SystemSetting
from audit_settings.utils import log_audit


class ReservationConflictError(Exception):
    def __init__(self, message, conflicts=None):
        super().__init__(message)
        self.conflicts = conflicts or []


class ReservationWorkflowError(Exception):
    pass


def check_time_interval_overlap(start1, end1, start2, end2):
    """
    Half-open interval overlap check [start, end).
    Overlap condition: start1 < end2 and end1 > start2.
    Adjacent intervals e.g. 9:00-10:00 and 10:00-11:00 do NOT overlap.
    """
    return (start1 < end2) and (end1 > start2)


def get_overlapping_approved_reservations(facility, start_time, end_time, exclude_reservation_id=None):
    """
    Returns QuerySet of APPROVED or CHECKED_IN reservations for facility overlapping [start_time, end_time).
    """
    qs = Reservation.objects.filter(
        facility=facility,
        status__in=[Reservation.STATUS_APPROVED, Reservation.STATUS_CHECKED_IN],
        start_time__lt=end_time,
        end_time__gt=start_time
    )
    if exclude_reservation_id:
        qs = qs.exclude(pk=exclude_reservation_id)
    return qs


def get_overlapping_active_reservations(facility, start_time, end_time, exclude_reservation_id=None):
    """
    Returns QuerySet of active reservations (PENDING, APPROVED, or CHECKED_IN) for facility overlapping [start_time, end_time).
    Pending requests immediately hold the slot to prevent conflicting submissions.
    """
    qs = Reservation.objects.filter(
        facility=facility,
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_APPROVED, Reservation.STATUS_CHECKED_IN],
        start_time__lt=end_time,
        end_time__gt=start_time
    )
    if exclude_reservation_id:
        qs = qs.exclude(pk=exclude_reservation_id)
    return qs


def get_overlapping_closures(facility, start_time, end_time, exclude_closure_id=None):
    """
    Returns QuerySet of active ClosureBlocks for facility overlapping [start_time, end_time).
    """
    qs = ClosureBlock.objects.filter(
        facility=facility,
        is_active=True,
        start_time__lt=end_time,
        end_time__gt=start_time
    )
    if exclude_closure_id:
        qs = qs.exclude(pk=exclude_closure_id)
    return qs


def validate_reservation_times_and_rules(facility, start_time, end_time, participant_count, is_submission=True):
    """
    Validates business rules for requested reservation slot.
    Returns list of error messages (empty if valid).
    """
    errors = []
    now = timezone.now()

    # 1. Facility active check
    if not facility.is_active:
        errors.append("Selected facility is currently archived or inactive.")

    # 2. Participant count vs Capacity
    if participant_count <= 0:
        errors.append("Participant count must be at least 1.")
    elif participant_count > facility.capacity:
        errors.append(f"Participant count ({participant_count}) exceeds facility capacity ({facility.capacity}).")

    # 3. Start time before end time
    if end_time <= start_time:
        errors.append("End time must be strictly after start time.")
        return errors

    # 4. Future start time check (only strictly enforced for regular submission/reschedule)
    if is_submission and start_time <= now:
        errors.append("Reservation start time must be in the future.")

    # 5. Single operating day check (Reject overnight reservations)
    if start_time.date() != end_time.date():
        errors.append("Overnight reservations are not permitted. Reservation must be within a single day.")
        return errors

    booking_date = start_time.date()

    # 6. Maximum advance booking window
    max_advance_days = SystemSetting.get_max_advance_days()
    advance_limit = timezone.localdate() + datetime.timedelta(days=max_advance_days)
    if is_submission and booking_date > advance_limit:
        errors.append(f"Reservation date exceeds maximum advance booking limit of {max_advance_days} days.")

    # 7. Maximum event duration
    max_duration_hours = SystemSetting.get_max_duration_hours()
    duration_hours = (end_time - start_time).total_seconds() / 3600.0
    if duration_hours > max_duration_hours:
        errors.append(f"Requested duration ({duration_hours:.1f} hrs) exceeds the maximum limit of {max_duration_hours} hours.")

    # 8. Facility operating hours for the given day
    is_closed, open_time, close_time = facility.get_operating_hours_for_date(booking_date)
    if is_closed:
        errors.append(f"Facility is closed on {booking_date.strftime('%A')}.")
    else:
        req_start_time = start_time.time()
        req_end_time = end_time.time()
        if req_start_time < open_time or req_end_time > close_time:
            errors.append(
                f"Requested hours ({req_start_time.strftime('%H:%M')} - {req_end_time.strftime('%H:%M')}) "
                f"fall outside facility operating hours ({open_time.strftime('%H:%M')} - {close_time.strftime('%H:%M')})."
            )

    return errors


def submit_reservation(user, facility, title, purpose, participant_count, start_time, end_time, request=None):
    """
    Submits a reservation request in PENDING status.
    """
    if not user.is_active:
        raise ValidationError("Inactive users cannot submit reservation requests.")

    errors = validate_reservation_times_and_rules(
        facility=facility,
        start_time=start_time,
        end_time=end_time,
        participant_count=participant_count,
        is_submission=True
    )
    if errors:
        raise ValidationError(errors)

    # Check active closure conflicts
    closure_conflicts = get_overlapping_closures(facility, start_time, end_time)
    if closure_conflicts.exists():
        raise ValidationError("The requested time slot is unavailable due to an active facility closure.")

    # Check existing active bookings and pending holds (zero conflicts policy)
    active_conflicts = get_overlapping_active_reservations(facility, start_time, end_time)
    if active_conflicts.exists():
        raise ValidationError("The requested time slot is unavailable. Please select another available schedule.")

    reference = Reservation.generate_reference()
    while Reservation.objects.filter(reference=reference).exists():
        reference = Reservation.generate_reference()

    with transaction.atomic():
        reservation = Reservation.objects.create(
            reference=reference,
            user=user,
            facility=facility,
            title=title.strip(),
            purpose=purpose.strip(),
            participant_count=participant_count,
            start_time=start_time,
            end_time=end_time,
            status=Reservation.STATUS_PENDING
        )

        log_audit(
            request=request,
            action='RESERVATION_SUBMITTED',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Reservation submitted for {facility.name} ({start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')})"
        )

    return reservation


def approve_reservation(reservation_id, admin_user, request=None):
    """
    Atomically approves a PENDING reservation.
    Implements row locking and conflict revalidation to prevent race conditions.
    """
    with _approval_concurrency_lock:
        try:
            with transaction.atomic():
                # Lock reservation row
                try:
                    reservation = Reservation.objects.select_for_update().get(id=reservation_id)
                except Reservation.DoesNotExist:
                    raise ReservationWorkflowError("Reservation does not exist.")

                # Lock facility row to serialize concurrent approvals for the same facility
                facility = Facility.objects.select_for_update().get(id=reservation.facility_id)

                # 1. Verify status is still PENDING
                if reservation.status != Reservation.STATUS_PENDING:
                    raise ReservationWorkflowError(
                        f"Cannot approve reservation with status '{reservation.get_status_display()}'. Must be Pending."
                    )

                # 2. Confirm facility is active
                if not facility.is_active:
                    raise ReservationWorkflowError("Cannot approve reservation: Facility is inactive or archived.")

                # 3. Capacity & rule revalidation
                rule_errors = validate_reservation_times_and_rules(
                    facility=facility,
                    start_time=reservation.start_time,
                    end_time=reservation.end_time,
                    participant_count=reservation.participant_count,
                    is_submission=False # Don't reject if start time is near
                )
                if rule_errors:
                    raise ReservationWorkflowError("; ".join(rule_errors))

                # 4. Check active closures
                active_closures = get_overlapping_closures(facility, reservation.start_time, reservation.end_time)
                if active_closures.exists():
                    raise ReservationConflictError("Cannot approve: Requested slot overlaps an active closure period.")

                # 5. Check overlapping APPROVED or CHECKED_IN reservations
                overlapping = get_overlapping_approved_reservations(
                    facility, reservation.start_time, reservation.end_time, exclude_reservation_id=reservation.id
                )
                if overlapping.exists():
                    conflict_refs = [r.reference for r in overlapping]
                    raise ReservationConflictError(
                        f"Conflict detected: Overlaps with approved reservation(s): {', '.join(conflict_refs)}",
                        conflicts=list(overlapping)
                    )

                # Update reservation status to APPROVED
                reservation.status = Reservation.STATUS_APPROVED
                reservation.decision_by = admin_user
                reservation.decision_at = timezone.now()
                reservation.save(update_fields=['status', 'decision_by', 'decision_at', 'updated_at'])

                # Ensure EventRecord is initialized
                EventRecord.objects.get_or_create(reservation=reservation)

                log_audit(
                    request=request,
                    action='RESERVATION_APPROVED',
                    target_type='Reservation',
                    target_id=str(reservation.id),
                    target_reference=reservation.reference,
                    details=f"Reservation approved by {admin_user.username}"
                )

                return reservation
        except (OperationalError, DatabaseError) as e:
            raise ReservationConflictError(
                "Concurrency conflict: The database locked this facility for a concurrent approval transaction. Please retry.",
                conflicts=[]
            ) from e


def reject_reservation(reservation_id, admin_user, reason, request=None):
    """
    Rejects a PENDING reservation with a mandatory reason.
    """
    if not reason or not reason.strip():
        raise ValidationError("Rejection reason is required.")

    with transaction.atomic():
        try:
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        except Reservation.DoesNotExist:
            raise ReservationWorkflowError("Reservation does not exist.")

        if reservation.status != Reservation.STATUS_PENDING:
            raise ReservationWorkflowError(
                f"Cannot reject reservation in '{reservation.get_status_display()}' state. Must be Pending."
            )

        reservation.status = Reservation.STATUS_REJECTED
        reservation.decision_by = admin_user
        reservation.decision_at = timezone.now()
        reservation.decision_reason = reason.strip()
        reservation.save(update_fields=['status', 'decision_by', 'decision_at', 'decision_reason', 'updated_at'])

        log_audit(
            request=request,
            action='RESERVATION_REJECTED',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Rejected by {admin_user.username}. Reason: {reason.strip()}"
        )

        return reservation


def reschedule_approved_reservation(reservation_id, new_start_time, new_end_time, reason, admin_user, request=None):
    """
    Reschedules an APPROVED reservation. Retains previous schedule history in ReservationChange.
    Atomic revalidation ensures intact original schedule if validation fails.
    """
    if not reason or not reason.strip():
        raise ValidationError("Rescheduling reason is required.")

    with _approval_concurrency_lock:
        with transaction.atomic():
            try:
                reservation = Reservation.objects.select_for_update().get(id=reservation_id)
            except Reservation.DoesNotExist:
                raise ReservationWorkflowError("Reservation does not exist.")

            facility = Facility.objects.select_for_update().get(id=reservation.facility_id)

            if reservation.status != Reservation.STATUS_APPROVED:
                raise ReservationWorkflowError("Only Approved reservations may be rescheduled.")

            # Revalidate with new times
            errors = validate_reservation_times_and_rules(
                facility=facility,
                start_time=new_start_time,
                end_time=new_end_time,
                participant_count=reservation.participant_count,
                is_submission=False
            )
            if errors:
                raise ValidationError(errors)

            # Check closures for new times
            closures = get_overlapping_closures(facility, new_start_time, new_end_time)
            if closures.exists():
                raise ReservationConflictError("New schedule overlaps with an active facility closure.")

            # Check conflicts with other active bookings
            conflicts = get_overlapping_active_reservations(
                facility, new_start_time, new_end_time, exclude_reservation_id=reservation.id
            )
            if conflicts.exists():
                raise ReservationConflictError("New schedule conflicts with an existing reservation.")

            # Record ReservationChange
            ReservationChange.objects.create(
                reservation=reservation,
                previous_start_time=reservation.start_time,
                previous_end_time=reservation.end_time,
                new_start_time=new_start_time,
                new_end_time=new_end_time,
                reason=reason.strip(),
                changed_by=admin_user
            )

            # Update reservation times
            old_start = reservation.start_time
            old_end = reservation.end_time
            reservation.start_time = new_start_time
            reservation.end_time = new_end_time
            reservation.save(update_fields=['start_time', 'end_time', 'updated_at'])

            log_audit(
                request=request,
                action='RESERVATION_RESCHEDULED',
                target_type='Reservation',
                target_id=str(reservation.id),
                target_reference=reservation.reference,
                details=(f"Rescheduled by {admin_user.username}. From {old_start.strftime('%Y-%m-%d %H:%M')}-{old_end.strftime('%H:%M')} "
                         f"to {new_start_time.strftime('%Y-%m-%d %H:%M')}-{new_end_time.strftime('%H:%M')}. Reason: {reason.strip()}")
            )

            return reservation


def cancel_reservation_by_user(reservation_id, user, request=None):
    """
    Cancels a user's own reservation before start time.
    """
    with transaction.atomic():
        try:
            reservation = Reservation.objects.select_for_update().get(id=reservation_id, user=user)
        except Reservation.DoesNotExist:
            raise ReservationWorkflowError("Reservation not found or unauthorized.")

        if not reservation.can_be_cancelled_by_user():
            raise ReservationWorkflowError(
                "You can only cancel Pending or Approved reservations before the scheduled start time."
            )

        reservation.status = Reservation.STATUS_CANCELLED
        reservation.save(update_fields=['status', 'updated_at'])

        log_audit(
            request=request,
            action='RESERVATION_CANCELLED',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Cancelled by user {user.username}"
        )

        return reservation


def cancel_reservation_by_admin(reservation_id, admin_user, reason, request=None):
    """
    Administrative cancellation with mandatory reason.
    """
    if not reason or not reason.strip():
        raise ValidationError("Cancellation reason is required.")

    with transaction.atomic():
        try:
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        except Reservation.DoesNotExist:
            raise ReservationWorkflowError("Reservation not found.")

        if reservation.status not in [Reservation.STATUS_PENDING, Reservation.STATUS_APPROVED]:
            raise ReservationWorkflowError("Only Pending or Approved reservations can be cancelled.")

        reservation.status = Reservation.STATUS_CANCELLED
        reservation.decision_reason = f"Admin cancellation: {reason.strip()}"
        reservation.save(update_fields=['status', 'decision_reason', 'updated_at'])

        log_audit(
            request=request,
            action='RESERVATION_CANCELLED',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Admin cancellation by {admin_user.username}. Reason: {reason.strip()}"
        )

        return reservation


def check_in_event(reservation_id, admin_user, actual_start_time=None, request=None):
    """
    Checks in an APPROVED reservation.
    """
    with transaction.atomic():
        try:
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        except Reservation.DoesNotExist:
            raise ReservationWorkflowError("Reservation not found.")

        if reservation.status != Reservation.STATUS_APPROVED:
            raise ReservationWorkflowError("Check-in is permitted only for Approved reservations.")

        now = timezone.now()
        act_start = actual_start_time or now

        reservation.status = Reservation.STATUS_CHECKED_IN
        reservation.save(update_fields=['status', 'updated_at'])

        event_record, _ = EventRecord.objects.get_or_create(reservation=reservation)
        event_record.check_in_time = now
        event_record.checked_in_by = admin_user
        event_record.actual_start_time = act_start
        event_record.save()

        log_audit(
            request=request,
            action='EVENT_CHECK_IN',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Checked in by {admin_user.username}"
        )

        return event_record


def complete_event(reservation_id, admin_user, actual_end_time=None, incident_notes="", completion_notes="", request=None):
    """
    Marks a CHECKED_IN event as COMPLETED.
    """
    with transaction.atomic():
        try:
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        except Reservation.DoesNotExist:
            raise ReservationWorkflowError("Reservation not found.")

        if reservation.status != Reservation.STATUS_CHECKED_IN:
            raise ReservationWorkflowError("Completion is permitted only after event check-in.")

        event_record = getattr(reservation, 'event_record', None)
        if not event_record or not event_record.actual_start_time:
            raise ReservationWorkflowError("Event record or actual start time missing.")

        now = timezone.now()
        act_end = actual_end_time or now

        if act_end < event_record.actual_start_time:
            raise ValidationError("Actual end time cannot precede actual start time.")

        reservation.status = Reservation.STATUS_COMPLETED
        reservation.save(update_fields=['status', 'updated_at'])

        event_record.actual_end_time = act_end
        event_record.completed_at = now
        event_record.completed_by = admin_user
        event_record.incident_notes = incident_notes.strip()
        event_record.completion_notes = completion_notes.strip()
        event_record.save()

        log_audit(
            request=request,
            action='EVENT_COMPLETED',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Event completed by {admin_user.username}"
        )

        return event_record


def mark_event_no_show(reservation_id, admin_user, no_show_notes="", request=None):
    """
    Marks an APPROVED reservation as NO SHOW.
    Permitted only after the scheduled end time has passed without check-in.
    """
    with transaction.atomic():
        try:
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        except Reservation.DoesNotExist:
            raise ReservationWorkflowError("Reservation not found.")

        if reservation.status != Reservation.STATUS_APPROVED:
            raise ReservationWorkflowError("No Show may be recorded only for Approved reservations that were never checked in.")

        now = timezone.now()
        if now < reservation.end_time:
            raise ReservationWorkflowError("No Show may be recorded only after the scheduled end time has passed.")

        reservation.status = Reservation.STATUS_NO_SHOW
        reservation.save(update_fields=['status', 'updated_at'])

        event_record, _ = EventRecord.objects.get_or_create(reservation=reservation)
        event_record.no_show_recorded_at = now
        event_record.no_show_recorded_by = admin_user
        event_record.no_show_notes = no_show_notes.strip()
        event_record.save()

        log_audit(
            request=request,
            action='EVENT_NO_SHOW',
            target_type='Reservation',
            target_id=str(reservation.id),
            target_reference=reservation.reference,
            details=f"Marked as No Show by {admin_user.username}. Notes: {no_show_notes.strip()}"
        )

        return event_record


def create_closure_block(facility, start_time, end_time, reason, admin_user, request=None):
    """
    Creates a facility closure block after ensuring no conflicting approved reservations exist.
    """
    if end_time <= start_time:
        raise ValidationError("End time must be strictly after start time.")

    if not reason or not reason.strip():
        raise ValidationError("Closure reason is required.")

    with transaction.atomic():
        # Check conflicting Approved or Checked In reservations
        conflicts = get_overlapping_approved_reservations(facility, start_time, end_time)
        if conflicts.exists():
            refs = [c.reference for c in conflicts]
            raise ReservationConflictError(
                f"Cannot create closure: {len(refs)} approved/checked-in reservation(s) exist during this interval: {', '.join(refs)}. "
                "Resolve them first by rescheduling or cancelling before creating closure.",
                conflicts=list(conflicts)
            )

        closure = ClosureBlock.objects.create(
            facility=facility,
            start_time=start_time,
            end_time=end_time,
            reason=reason.strip(),
            is_active=True,
            created_by=admin_user
        )

        log_audit(
            request=request,
            action='CLOSURE_CREATED',
            target_type='ClosureBlock',
            target_id=str(closure.id),
            target_reference=f"Closure for {facility.name}",
            details=f"Closure from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}. Reason: {reason.strip()}"
        )

        return closure


def archive_closure_block(closure_id, admin_user, request=None):
    """
    Archives an active closure block.
    """
    with transaction.atomic():
        closure = ClosureBlock.objects.select_for_update().get(id=closure_id)
        closure.is_active = False
        closure.save(update_fields=['is_active', 'updated_at'])

        log_audit(
            request=request,
            action='CLOSURE_ARCHIVED',
            target_type='ClosureBlock',
            target_id=str(closure.id),
            target_reference=f"Closure for {closure.facility.name}",
            details=f"Archived by {admin_user.username}"
        )
        return closure


def calculate_facility_slots(facility, target_date):
    """
    Calculates hourly availability slots for a facility on a specific date.
    Returns list of slot dicts: [{'start_time': '08:00', 'end_time': '09:00', 'is_available': bool, 'reason': str}]
    Adheres strictly to privacy requirement: doesn't reveal whether a slot is pending,
    approved, or under closure. All unavailable slots simply display 'Unavailable'.
    """
    is_closed, open_time, close_time = facility.get_operating_hours_for_date(target_date)
    if is_closed or not open_time or not close_time:
        return {
            'is_closed': True,
            'open_time': open_time.strftime('%H:%M') if open_time else None,
            'close_time': close_time.strftime('%H:%M') if close_time else None,
            'open_time_display': open_time.strftime('%I:%M %p').lstrip('0') if open_time else '',
            'close_time_display': close_time.strftime('%I:%M %p').lstrip('0') if close_time else '',
            'open_time_obj': open_time,
            'close_time_obj': close_time,
            'slots': []
        }

    # Fetch active closures for this day
    day_start = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time.min))
    day_end = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time.max))

    closures = ClosureBlock.objects.filter(
        facility=facility,
        is_active=True,
        start_time__lt=day_end,
        end_time__gt=day_start
    )

    # Fetch active bookings (PENDING, APPROVED, CHECKED_IN) for this day
    active_bookings = Reservation.objects.filter(
        facility=facility,
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_APPROVED, Reservation.STATUS_CHECKED_IN],
        start_time__lt=day_end,
        end_time__gt=day_start
    )

    slots = []
    current_time = open_time
    now = timezone.now()

    # Generate 1-hour slots from open_time to close_time
    while current_time < close_time:
        slot_start_dt = timezone.make_aware(datetime.datetime.combine(target_date, current_time))
        # slot end is current_time + 1 hour or close_time
        next_hour = (datetime.datetime.combine(target_date, current_time) + datetime.timedelta(hours=1)).time()
        slot_end_time = min(next_hour, close_time)
        slot_end_dt = timezone.make_aware(datetime.datetime.combine(target_date, slot_end_time))

        # Check closure overlap
        has_closure = closures.filter(start_time__lt=slot_end_dt, end_time__gt=slot_start_dt).exists()
        # Check active booking overlap (pending holds, approved, checked-in)
        has_booking = active_bookings.filter(start_time__lt=slot_end_dt, end_time__gt=slot_start_dt).exists()
        # Check if slot is in the past
        is_past = slot_start_dt <= now

        is_available = not (has_closure or has_booking or is_past)
        # Generic label for non-available slots to prevent privacy leaks or favoritism
        reason = "Available" if is_available else "Unavailable"

        slots.append({
            'start_time': current_time.strftime('%H:%M'),
            'end_time': slot_end_time.strftime('%H:%M'),
            'start_display': slot_start_dt.strftime('%I:%M %p').lstrip('0'),
            'end_display': slot_end_dt.strftime('%I:%M %p').lstrip('0'),
            'start_iso': slot_start_dt.strftime('%Y-%m-%dT%H:%M'),
            'end_iso': slot_end_dt.strftime('%Y-%m-%dT%H:%M'),
            'is_available': is_available,
            'reason': reason
        })

        current_time = slot_end_time

    return {
        'is_closed': False,
        'open_time': open_time.strftime('%H:%M'),
        'close_time': close_time.strftime('%H:%M'),
        'open_time_display': open_time.strftime('%I:%M %p').lstrip('0'),
        'close_time_display': close_time.strftime('%I:%M %p').lstrip('0'),
        'open_time_obj': open_time,
        'close_time_obj': close_time,
        'slots': slots
    }
