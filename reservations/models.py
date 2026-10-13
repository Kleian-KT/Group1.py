import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from facilities.models import Facility


class Reservation(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHECKED_IN = 'CHECKED_IN'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_NO_SHOW = 'NO_SHOW'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_CHECKED_IN, 'Checked In'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_NO_SHOW, 'No Show'),
    )

    reference = models.CharField(max_length=32, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservations')
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name='reservations')
    title = models.CharField(max_length=200)
    purpose = models.TextField()
    participant_count = models.PositiveIntegerField()
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    # Decision metadata
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decided_reservations'
    )
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reservation'
        verbose_name_plural = 'Reservations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.title} ({self.get_status_display()})"

    @staticmethod
    def generate_reference():
        now_str = timezone.now().strftime('%Y%m')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"RES-{now_str}-{unique_suffix}"

    def can_be_cancelled_by_user(self):
        """User may cancel their own Pending or Approved reservation before start time."""
        return self.status in [self.STATUS_PENDING, self.STATUS_APPROVED] and timezone.now() < self.start_time

    @property
    def duration_hours(self):
        diff = self.end_time - self.start_time
        return round(diff.total_seconds() / 3600.0, 2)


class ClosureBlock(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name='closures')
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    reason = models.TextField()
    is_active = models.BooleanField(default=True, help_text="Active or archived closure")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_closures')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Closure Block'
        verbose_name_plural = 'Closure Blocks'
        ordering = ['-start_time']

    def __str__(self):
        return f"Closure: {self.facility.name} ({self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')})"


class ReservationChange(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='changes')
    previous_start_time = models.DateTimeField()
    previous_end_time = models.DateTimeField()
    new_start_time = models.DateTimeField()
    new_end_time = models.DateTimeField()
    reason = models.TextField()
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='rescheduled_reservations')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reservation Change'
        verbose_name_plural = 'Reservation Changes'
        ordering = ['-changed_at']

    def __str__(self):
        return f"Change for {self.reservation.reference} on {self.changed_at.strftime('%Y-%m-%d %H:%M')}"
