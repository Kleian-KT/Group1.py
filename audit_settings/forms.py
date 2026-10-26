from django import forms
from django.core.exceptions import ValidationError


class SystemSettingsForm(forms.Form):
    max_event_duration_hours = forms.IntegerField(
        min_value=1,
        max_value=24,
        label="Maximum Event Duration (Hours)",
        help_text="Maximum allowed continuous hours per reservation (e.g. 4)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 24})
    )
    max_advance_booking_days = forms.IntegerField(
        min_value=1,
        max_value=365,
        label="Maximum Advance Booking Window (Days)",
        help_text="Maximum number of calendar days in advance a user may submit a reservation (e.g. 30)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 365})
    )

    def clean_max_event_duration_hours(self):
        val = self.cleaned_data.get('max_event_duration_hours')
        if val is None or val < 1 or val > 24:
            raise ValidationError("Maximum event duration must be between 1 and 24 hours.")
        return val

    def clean_max_advance_booking_days(self):
        val = self.cleaned_data.get('max_advance_booking_days')
        if val is None or val < 1 or val > 365:
            raise ValidationError("Maximum advance booking window must be between 1 and 365 days.")
        return val
