import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone

from facilities.models import Facility, FacilityCategory, Amenity, FacilityAmenity, FacilityOperatingHour
from facilities.forms import (
    FacilityForm, FacilityCategoryForm, AmenityForm, 
    FacilityAmenityForm, FacilityOperatingHourForm
)
from reservations.models import Reservation
from reservations.services import calculate_facility_slots
from accounts.permissions import admin_required, active_user_required
from audit_settings.utils import log_audit


# -------------------------------------------------------------
# A2 — Admin Facility Management
# -------------------------------------------------------------

@admin_required
def admin_facility_list(request):
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()

    facilities_qs = Facility.objects.select_related('category').all().order_by('name')

    if search_query:
        facilities_qs = facilities_qs.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    if category_id:
        facilities_qs = facilities_qs.filter(category_id=category_id)

    if status_filter == 'active':
        facilities_qs = facilities_qs.filter(is_active=True)
    elif status_filter == 'archived':
        facilities_qs = facilities_qs.filter(is_active=False)

    categories = FacilityCategory.objects.all()

    paginator = Paginator(facilities_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'manage/facility_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'status_filter': status_filter,
        'active_menu': 'facilities'
    })


@admin_required
def admin_facility_create(request):
    if request.method == 'POST':
        form = FacilityForm(request.POST)
        if form.is_valid():
            facility = form.save()
            log_audit(
                request=request,
                action='FACILITY_CREATED',
                target_type='Facility',
                target_id=str(facility.id),
                target_reference=facility.code,
                details=f"Facility created: {facility.name} (Capacity: {facility.capacity})"
            )
            messages.success(request, f"Facility '{facility.name}' created successfully.")
            return redirect('admin_facility_detail', facility_id=facility.id)
    else:
        form = FacilityForm()

    return render(request, 'manage/facility_form.html', {
        'form': form,
        'action_title': 'Add New Facility',
        'active_menu': 'facilities'
    })


@admin_required
def admin_facility_detail(request, facility_id):
    facility = get_object_or_404(Facility.objects.select_related('category'), id=facility_id)
    amenities = facility.facility_amenities.select_related('amenity').all()
    operating_hours = facility.operating_hours.all()
    recent_reservations = facility.reservations.select_related('user').order_by('-start_time')[:10]

    amenity_form = FacilityAmenityForm()
    hour_form = FacilityOperatingHourForm()

    return render(request, 'manage/facility_detail.html', {
        'facility': facility,
        'amenities': amenities,
        'operating_hours': operating_hours,
        'recent_reservations': recent_reservations,
        'amenity_form': amenity_form,
        'hour_form': hour_form,
        'active_menu': 'facilities'
    })


@admin_required
def admin_facility_edit(request, facility_id):
    facility = get_object_or_404(Facility, id=facility_id)
    if request.method == 'POST':
        form = FacilityForm(request.POST, instance=facility)
        if form.is_valid():
            form.save()
            log_audit(
                request=request,
                action='FACILITY_UPDATED',
                target_type='Facility',
                target_id=str(facility.id),
                target_reference=facility.code,
                details=f"Facility updated: {facility.name}"
            )
            messages.success(request, f"Facility '{facility.name}' updated successfully.")
            return redirect('admin_facility_detail', facility_id=facility.id)
    else:
        form = FacilityForm(instance=facility)

    return render(request, 'manage/facility_form.html', {
        'form': form,
        'facility': facility,
        'action_title': f'Edit Facility: {facility.name}',
        'active_menu': 'facilities'
    })


@admin_required
@require_POST
def admin_facility_archive(request, facility_id):
    facility = get_object_or_404(Facility, id=facility_id)
    facility.is_active = not facility.is_active
    facility.save(update_fields=['is_active'])

    action_label = "FACILITY_UPDATED" if facility.is_active else "FACILITY_ARCHIVED"
    status_msg = "reactivated" if facility.is_active else "archived"

    log_audit(
        request=request,
        action=action_label,
        target_type='Facility',
        target_id=str(facility.id),
        target_reference=facility.code,
        details=f"Facility {facility.code} {status_msg} by {request.user.username}"
    )
    messages.success(request, f"Facility '{facility.name}' has been {status_msg}.")
    return redirect('admin_facility_detail', facility_id=facility.id)


@admin_required
@require_POST
def admin_facility_add_amenity(request, facility_id):
    facility = get_object_or_404(Facility, id=facility_id)
    form = FacilityAmenityForm(request.POST)
    if form.is_valid():
        facility_amenity = form.save(commit=False)
        facility_amenity.facility = facility
        if FacilityAmenity.objects.filter(facility=facility, amenity=facility_amenity.amenity).exists():
            messages.error(request, "This amenity is already assigned to the facility.")
        else:
            facility_amenity.save()
            messages.success(request, f"Amenity '{facility_amenity.amenity.name}' assigned to {facility.name}.")
    else:
        messages.error(request, "Error adding amenity. Please check input values.")
    return redirect('admin_facility_detail', facility_id=facility.id)


@admin_required
@require_POST
def admin_facility_remove_amenity(request, facility_id, amenity_id):
    facility = get_object_or_404(Facility, id=facility_id)
    assoc = get_object_or_404(FacilityAmenity, facility=facility, id=amenity_id)
    assoc.delete()
    messages.success(request, "Amenity removed from facility.")
    return redirect('admin_facility_detail', facility_id=facility.id)


@admin_required
@require_POST
def admin_facility_save_operating_hour(request, facility_id):
    facility = get_object_or_404(Facility, id=facility_id)
    form = FacilityOperatingHourForm(request.POST)
    if form.is_valid():
        day_of_week = form.cleaned_data['day_of_week']
        obj, created = FacilityOperatingHour.objects.update_or_create(
            facility=facility,
            day_of_week=day_of_week,
            defaults={
                'open_time': form.cleaned_data['open_time'],
                'close_time': form.cleaned_data['close_time'],
                'is_closed': form.cleaned_data['is_closed']
            }
        )
        action_verb = "created" if created else "updated"
        messages.success(request, f"Operating schedule for {obj.get_day_of_week_display()} {action_verb}.")
    else:
        messages.error(request, "Failed to update operating hours. Closing time must be after opening time.")
    return redirect('admin_facility_detail', facility_id=facility.id)


# -------------------------------------------------------------
# Categories Management
# -------------------------------------------------------------

@admin_required
def admin_category_list(request):
    if request.method == 'POST':
        form = FacilityCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            log_audit(
                request=request,
                action='CATEGORY_CREATED',
                target_type='FacilityCategory',
                target_id=str(cat.id),
                target_reference=cat.name,
                details=f"Category created: {cat.name}"
            )
            messages.success(request, f"Category '{cat.name}' created.")
            return redirect('admin_category_list')
    else:
        form = FacilityCategoryForm()

    categories = FacilityCategory.objects.all().order_by('name')
    return render(request, 'manage/category_list.html', {
        'categories': categories,
        'form': form,
        'active_menu': 'facilities'
    })


@admin_required
@require_POST
def admin_category_archive(request, category_id):
    cat = get_object_or_404(FacilityCategory, id=category_id)
    cat.is_active = not cat.is_active
    cat.save(update_fields=['is_active'])
    status_str = "activated" if cat.is_active else "archived"
    log_audit(
        request=request,
        action='CATEGORY_ARCHIVED' if not cat.is_active else 'CATEGORY_UPDATED',
        target_type='FacilityCategory',
        target_id=str(cat.id),
        target_reference=cat.name,
        details=f"Category '{cat.name}' {status_str}"
    )
    messages.success(request, f"Category '{cat.name}' {status_str}.")
    return redirect('admin_category_list')


# -------------------------------------------------------------
# Amenities Management
# -------------------------------------------------------------

@admin_required
def admin_amenity_list(request):
    if request.method == 'POST':
        form = AmenityForm(request.POST)
        if form.is_valid():
            amenity = form.save()
            log_audit(
                request=request,
                action='AMENITY_CREATED',
                target_type='Amenity',
                target_id=str(amenity.id),
                target_reference=amenity.name,
                details=f"Amenity created: {amenity.name}"
            )
            messages.success(request, f"Amenity '{amenity.name}' created.")
            return redirect('admin_amenity_list')
    else:
        form = AmenityForm()

    amenities = Amenity.objects.all().order_by('name')
    return render(request, 'manage/amenity_list.html', {
        'amenities': amenities,
        'form': form,
        'active_menu': 'facilities'
    })


@admin_required
@require_POST
def admin_amenity_archive(request, amenity_id):
    amenity = get_object_or_404(Amenity, id=amenity_id)
    amenity.is_active = not amenity.is_active
    amenity.save(update_fields=['is_active'])
    status_str = "activated" if amenity.is_active else "archived"
    log_audit(
        request=request,
        action='AMENITY_ARCHIVED' if not amenity.is_active else 'AMENITY_UPDATED',
        target_type='Amenity',
        target_id=str(amenity.id),
        target_reference=amenity.name,
        details=f"Amenity '{amenity.name}' {status_str}"
    )
    messages.success(request, f"Amenity '{amenity.name}' {status_str}.")
    return redirect('admin_amenity_list')


# -------------------------------------------------------------
# U2 — Basic User Facility Browsing and Availability
# -------------------------------------------------------------

@active_user_required
def user_facility_list(request):
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    min_capacity = request.GET.get('capacity', '').strip()

    facilities_qs = Facility.objects.filter(is_active=True).select_related('category').prefetch_related('facility_amenities__amenity')

    if search_query:
        facilities_qs = facilities_qs.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if category_id:
        facilities_qs = facilities_qs.filter(category_id=category_id)

    if min_capacity and min_capacity.isdigit():
        facilities_qs = facilities_qs.filter(capacity__gte=int(min_capacity))

    categories = FacilityCategory.objects.filter(is_active=True)

    paginator = Paginator(facilities_qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'portal/facility_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'min_capacity': min_capacity,
        'active_menu': 'facilities'
    })


@active_user_required
def user_facility_detail(request, facility_id):
    facility = get_object_or_404(Facility.objects.filter(is_active=True), id=facility_id)
    amenities = facility.facility_amenities.select_related('amenity').all()

    # Availability date selector (defaults to tomorrow)
    date_str = request.GET.get('date', '').strip()
    selected_date = None
    if date_str:
        try:
            selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date() + datetime.timedelta(days=1)
    else:
        selected_date = timezone.now().date() + datetime.timedelta(days=1)

    availability_data = calculate_facility_slots(facility, selected_date)

    return render(request, 'portal/facility_detail.html', {
        'facility': facility,
        'amenities': amenities,
        'selected_date': selected_date,
        'availability': availability_data,
        'active_menu': 'facilities'
    })
