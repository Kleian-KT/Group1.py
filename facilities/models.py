import datetime
from django.db import models


class FacilityCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Active or archived status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Facility Category'
        verbose_name_plural = 'Facility Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Facility(models.Model):
    code = models.CharField(max_length=30, unique=True, help_text="Unique facility code (e.g. AUD-101)")
    name = models.CharField(max_length=150)
    category = models.ForeignKey(FacilityCategory, on_delete=models.PROTECT, related_name='facilities')
    location = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField(help_text="Maximum participant capacity")
    description = models.TextField(blank=True)
    
    # Default operating hours (fallback when day-specific schedule is not configured)
    default_open_time = models.TimeField(default=datetime.time(8, 0), help_text="Default opening time")
    default_close_time = models.TimeField(default=datetime.time(21, 0), help_text="Default closing time")
    
    is_active = models.BooleanField(default=True, help_text="Active or archived status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_operating_hours_for_date(self, target_date):
        """
        Returns a tuple: (is_closed, open_time, close_time) for a given date (datetime.date).
        """
        weekday = target_date.weekday() # 0 = Monday, 6 = Sunday
        specific = self.operating_hours.filter(day_of_week=weekday).first()
        if specific:
            return (specific.is_closed, specific.open_time, specific.close_time)
        return (False, self.default_open_time, self.default_close_time)


class FacilityOperatingHour(models.Model):
    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='operating_hours')
    day_of_week = models.IntegerField(choices=WEEKDAY_CHOICES)
    open_time = models.TimeField(default=datetime.time(8, 0))
    close_time = models.TimeField(default=datetime.time(21, 0))
    is_closed = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Facility Operating Hour'
        verbose_name_plural = 'Facility Operating Hours'
        unique_together = ('facility', 'day_of_week')
        ordering = ['facility', 'day_of_week']

    def __str__(self):
        day_name = dict(self.WEEKDAY_CHOICES).get(self.day_of_week, '')
        if self.is_closed:
            return f"{self.facility.code} - {day_name}: Closed"
        return f"{self.facility.code} - {day_name}: {self.open_time.strftime('%H:%M')} - {self.close_time.strftime('%H:%M')}"


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-check-circle', help_text="Bootstrap Icons CSS class")
    is_active = models.BooleanField(default=True, help_text="Active or archived status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Amenity'
        verbose_name_plural = 'Amenities'
        ordering = ['name']

    def __str__(self):
        return self.name


class FacilityAmenity(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='facility_amenities')
    amenity = models.ForeignKey(Amenity, on_delete=models.PROTECT, related_name='facility_amenities')
    quantity = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Facility Amenity'
        verbose_name_plural = 'Facility Amenities'
        unique_together = ('facility', 'amenity')
        ordering = ['facility', 'amenity']

    def __str__(self):
        return f"{self.facility.name} - {self.amenity.name} ({self.quantity})"
