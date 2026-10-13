from django import forms


class SystemSettingsForm(forms.Form):
    max_event_duration_hours = forms.IntegerField(
        min_value=1,
        max_value=24,
        label="Maximum Event Duration (Hours)",
        help_text="Maximum allowed continuous hours per reservation (e.g. 4)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    max_advance_booking_days = forms.IntegerField(
        min_value=1,
        max_value=365,
        label="Maximum Advance Booking Window (Days)",
        help_text="Maximum number of calendar days in advance a user may submit a reservation (e.g. 30)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
