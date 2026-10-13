import csv
import datetime
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Count, Q, F
from django.utils import timezone

from facilities.models import Facility
from reservations.models import Reservation
from accounts.permissions import admin_required


def sanitize_csv_cell(value):
    """
    Prevents spreadsheet formula injection if cell begins with =, +, -, @.
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ['=', '+', '-', '@', '\t', '\r']:
        return f"'{val_str}"
    return val_str


@admin_required
def admin_reports(request):
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    facility_id = request.GET.get('facility', '').strip()
    status_filter = request.GET.get('status', '').strip()

    now = timezone.now()
    # Default to past 30 days if not specified
    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = (now - datetime.timedelta(days=30)).date()
    else:
        start_date = (now - datetime.timedelta(days=30)).date()

    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = now.date()
    else:
        end_date = now.date()

    start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))

    # Base reservations query for reporting
    res_qs = Reservation.objects.filter(
        start_time__lte=end_dt,
        start_time__gte=start_dt
    ).select_related('facility', 'user')

    if facility_id:
        res_qs = res_qs.filter(facility_id=facility_id)

    if status_filter:
        res_qs = res_qs.filter(status=status_filter)

    reservations_list = res_qs.order_by('-start_time')

    # Aggregated Summary Stats
    total_reservations = res_qs.count()
    approved_count = res_qs.filter(status=Reservation.STATUS_APPROVED).count()
    completed_count = res_qs.filter(status=Reservation.STATUS_COMPLETED).count()
    no_show_count = res_qs.filter(status=Reservation.STATUS_NO_SHOW).count()
    rejected_count = res_qs.filter(status=Reservation.STATUS_REJECTED).count()
    cancelled_count = res_qs.filter(status=Reservation.STATUS_CANCELLED).count()

    # Facility Utilization Calculation
    facilities = Facility.objects.all().order_by('name')
    utilization_data = []

    for fac in facilities:
        fac_bookings = Reservation.objects.filter(
            facility=fac,
            start_time__lte=end_dt,
            start_time__gte=start_dt,
            status__in=[
                Reservation.STATUS_APPROVED,
                Reservation.STATUS_CHECKED_IN,
                Reservation.STATUS_COMPLETED
            ]
        )

        total_booked_seconds = 0
        for b in fac_bookings:
            diff = b.end_time - b.start_time
            total_booked_seconds += diff.total_seconds()

        booked_hours = round(total_booked_seconds / 3600.0, 2)
        completed_events = fac_bookings.filter(status=Reservation.STATUS_COMPLETED).count()

        utilization_data.append({
            'facility': fac,
            'booking_count': fac_bookings.count(),
            'booked_hours': booked_hours,
            'completed_events': completed_events
        })

    return render(request, 'manage/reports.html', {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'facility_id': facility_id,
        'status_filter': status_filter,
        'facilities': facilities,
        'statuses': Reservation.STATUS_CHOICES,
        'total_reservations': total_reservations,
        'approved_count': approved_count,
        'completed_count': completed_count,
        'no_show_count': no_show_count,
        'rejected_count': rejected_count,
        'cancelled_count': cancelled_count,
        'reservations_list': reservations_list[:100], # display up to 100 in table
        'utilization_data': utilization_data,
        'active_menu': 'reports'
    })


@admin_required
def admin_reports_export_csv(request):
    report_type = request.GET.get('report_type', 'reservations').strip()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    facility_id = request.GET.get('facility', '').strip()
    status_filter = request.GET.get('status', '').strip()

    now = timezone.now()
    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = (now - datetime.timedelta(days=30)).date()
    else:
        start_date = (now - datetime.timedelta(days=30)).date()

    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = now.date()
    else:
        end_date = now.date()

    start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    timestamp_str = now.strftime('%Y%m%d_%H%M')

    if report_type == 'utilization':
        response['Content-Disposition'] = f'attachment; filename="facility_utilization_report_{timestamp_str}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Facility Code', 'Facility Name', 'Capacity', 'Location', 'Total Active Bookings', 'Total Booked Hours', 'Completed Events'])

        facilities = Facility.objects.all().order_by('name')
        for fac in facilities:
            fac_bookings = Reservation.objects.filter(
                facility=fac,
                start_time__lte=end_dt,
                start_time__gte=start_dt,
                status__in=[
                    Reservation.STATUS_APPROVED,
                    Reservation.STATUS_CHECKED_IN,
                    Reservation.STATUS_COMPLETED
                ]
            )
            total_seconds = sum((b.end_time - b.start_time).total_seconds() for b in fac_bookings)
            booked_hours = round(total_seconds / 3600.0, 2)
            completed_events = fac_bookings.filter(status=Reservation.STATUS_COMPLETED).count()

            writer.writerow([
                sanitize_csv_cell(fac.code),
                sanitize_csv_cell(fac.name),
                sanitize_csv_cell(fac.capacity),
                sanitize_csv_cell(fac.location),
                sanitize_csv_cell(fac_bookings.count()),
                sanitize_csv_cell(booked_hours),
                sanitize_csv_cell(completed_events),
            ])
    else:
        response['Content-Disposition'] = f'attachment; filename="reservations_report_{timestamp_str}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Reference', 'Status', 'Facility Code', 'Facility Name', 'Applicant Username',
            'Applicant Name', 'Event Title', 'Participant Count', 'Start Time', 'End Time',
            'Duration (Hours)', 'Decision By', 'Submission Date'
        ])

        res_qs = Reservation.objects.filter(
            start_time__lte=end_dt,
            start_time__gte=start_dt
        ).select_related('facility', 'user', 'decision_by').order_by('-start_time')

        if facility_id:
            res_qs = res_qs.filter(facility_id=facility_id)
        if status_filter:
            res_qs = res_qs.filter(status=status_filter)

        for r in res_qs:
            writer.writerow([
                sanitize_csv_cell(r.reference),
                sanitize_csv_cell(r.get_status_display()),
                sanitize_csv_cell(r.facility.code),
                sanitize_csv_cell(r.facility.name),
                sanitize_csv_cell(r.user.username),
                sanitize_csv_cell(r.user.display_name),
                sanitize_csv_cell(r.title),
                sanitize_csv_cell(r.participant_count),
                sanitize_csv_cell(r.start_time.strftime('%Y-%m-%d %H:%M')),
                sanitize_csv_cell(r.end_time.strftime('%Y-%m-%d %H:%M')),
                sanitize_csv_cell(r.duration_hours),
                sanitize_csv_cell(r.decision_by.username if r.decision_by else "N/A"),
                sanitize_csv_cell(r.created_at.strftime('%Y-%m-%d %H:%M')),
            ])

    return response
