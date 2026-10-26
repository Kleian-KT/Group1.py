import os
import datetime
from django.db import models
from django.conf import settings


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
    custom_image_url = models.URLField(max_length=500, blank=True, default='', help_text="Direct venue photo URL (optional)")
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

    def get_image_url(self):
        """Returns authentic BulSU venue photo from static files, custom URL, or fallback."""
        if self.custom_image_url:
            return self.custom_image_url

        code_lower = (self.code or '').lower().strip()
        local_disk_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'facilities', f"{code_lower}.jpg")
        if os.path.exists(local_disk_path):
            return f"/static/img/facilities/{code_lower}.jpg"

        code_upper = (self.code or '').upper()
        cat_lower = (self.category.name or '').lower() if self.category else ''

        if 'VAL' in code_upper or 'GYM' in code_upper:
            # Valencia Hall Gymnasium / Athletic Arena
            return 'https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=1200&q=80'
        elif 'FED' in code_upper or ('AVR' in code_upper and 'ROX' not in code_upper):
            # Federizo Hall Audio-Visual Theater
            return 'https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=1200&q=80'
        elif 'ELIB' in code_upper or 'LIB' in code_upper:
            # BulSU E-Library Multimedia Conference Center
            return 'https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1200&q=80'
        elif 'CICT' in code_upper or 'LAB' in code_upper:
            # CICT Advanced Computer & Software Lab
            return 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80'
        elif 'NAT' in code_upper or 'ENG' in code_upper:
            # Natividad Hall Engineering Amphitheater
            return 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=1200&q=80'
        elif 'ALV' in code_upper or 'CIT' in code_upper:
            # Alvarado Hall Function Hall
            return 'https://images.unsplash.com/photo-1511578314322-379afb476865?auto=format&fit=crop&w=1200&q=80'
        elif 'ROX' in code_upper or 'COED' in code_upper:
            # Roxas Hall Audio-Visual Presentation Hall
            return 'https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?auto=format&fit=crop&w=1200&q=80'
        elif 'SAC' in code_upper:
            # Student Activity Center Grand Hall
            return 'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?auto=format&fit=crop&w=1200&q=80'
        elif 'HOST' in code_upper:
            # University Hostel Grand Ballroom
            return 'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&w=1200&q=80'
        elif 'FLR' in code_upper or 'CONF' in code_upper:
            # Flores Hall Executive Boardroom
            return 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80'
        elif 'auditorium' in cat_lower or 'theater' in cat_lower:
            return 'https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=1200&q=80'
        elif 'multipurpose' in cat_lower or 'hall' in cat_lower:
            return 'https://images.unsplash.com/photo-1511578314322-379afb476865?auto=format&fit=crop&w=1200&q=80'
        elif 'laborator' in cat_lower:
            return 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80'
        return 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80'

    @property
    def image_url(self):
        return self.get_image_url()

    @property
    def badge_color(self):
        code_upper = (self.code or '').upper()
        if 'VAL' in code_upper or 'GYM' in code_upper:
            return 'bg-[#6b1414] text-white' # BulSU Maroon
        elif 'FED' in code_upper:
            return 'bg-[#831843] text-white'
        elif 'ELIB' in code_upper or 'LIB' in code_upper:
            return 'bg-[#1e40af] text-white'
        elif 'CICT' in code_upper or 'LAB' in code_upper:
            return 'bg-[#003e38] text-[#89f5e7]'
        elif 'NAT' in code_upper or 'ENG' in code_upper:
            return 'bg-[#b45309] text-white' # Amber/Gold
        elif 'ALV' in code_upper or 'CIT' in code_upper:
            return 'bg-[#904d00] text-white'
        elif 'ROX' in code_upper:
            return 'bg-[#4c1d95] text-white'
        elif 'SAC' in code_upper:
            return 'bg-[#0f766e] text-white'
        elif 'HOST' in code_upper:
            return 'bg-[#4338ca] text-white'
        elif 'FLR' in code_upper or 'CONF' in code_upper:
            return 'bg-[#1e293b] text-white'
        return 'bg-[#6b1414] text-white'


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
