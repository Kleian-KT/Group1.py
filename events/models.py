from django.db import models
from django.conf import settings
from reservations.models import Reservation


class EventRecord(models.Model):
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='event_record',
        help_text="One operational record per booking"
    )
    # Check-in
    check_in_time = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checked_in_events'
    )
    
    # Operational execution
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_events'
    )
    completion_notes = models.TextField(blank=True)
    
    # No Show
    no_show_recorded_at = models.DateTimeField(null=True, blank=True)
    no_show_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='no_show_events'
    )
    no_show_notes = models.TextField(blank=True)
    
    # Incident notes
    incident_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Record'
        verbose_name_plural = 'Event Records'
        ordering = ['-created_at']

    def __str__(self):
        return f"Event Record: {self.reservation.reference}"
