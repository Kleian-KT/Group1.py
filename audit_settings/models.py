from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('RESERVATION_SUBMITTED', 'Reservation Submitted'),
        ('RESERVATION_APPROVED', 'Reservation Approved'),
        ('RESERVATION_REJECTED', 'Reservation Rejected'),
        ('RESERVATION_CANCELLED', 'Reservation Cancelled'),
        ('RESERVATION_RESCHEDULED', 'Reservation Rescheduled'),
        ('EVENT_CHECK_IN', 'Event Checked In'),
        ('EVENT_COMPLETED', 'Event Completed'),
        ('EVENT_NO_SHOW', 'Event Marked No Show'),
        ('CLOSURE_CREATED', 'Closure Period Created'),
        ('CLOSURE_ARCHIVED', 'Closure Period Archived'),
        ('ACCOUNT_ACTIVATED', 'Account Activated'),
        ('ACCOUNT_DEACTIVATED', 'Account Deactivated'),
        ('FACILITY_CREATED', 'Facility Created'),
        ('FACILITY_UPDATED', 'Facility Updated'),
        ('FACILITY_ARCHIVED', 'Facility Archived'),
        ('CATEGORY_CREATED', 'Category Created'),
        ('CATEGORY_UPDATED', 'Category Updated'),
        ('CATEGORY_ARCHIVED', 'Category Archived'),
        ('AMENITY_CREATED', 'Amenity Created'),
        ('AMENITY_UPDATED', 'Amenity Updated'),
        ('AMENITY_ARCHIVED', 'Amenity Archived'),
        ('SETTINGS_UPDATED', 'System Settings Updated'),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.CharField(max_length=60, blank=True)
    target_reference = models.CharField(max_length=150, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {actor_name} -> {self.action} on {self.target_reference}"


class SystemSetting(models.Model):
    MAX_DURATION_KEY = 'max_event_duration_hours'
    MAX_ADVANCE_WINDOW_KEY = 'max_advance_booking_days'

    key = models.CharField(max_length=60, unique=True)
    value = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get_max_duration_hours(cls):
        setting = cls.objects.filter(key=cls.MAX_DURATION_KEY).first()
        if setting:
            try:
                return int(setting.value)
            except ValueError:
                pass
        return 4 # Default 4 hours

    @classmethod
    def get_max_advance_days(cls):
        setting = cls.objects.filter(key=cls.MAX_ADVANCE_WINDOW_KEY).first()
        if setting:
            try:
                return int(setting.value)
            except ValueError:
                pass
        return 30 # Default 30 calendar days
