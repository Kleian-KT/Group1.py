import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone


class EventCheckInForm(forms.Form):
    actual_start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=False,
        label="Actual Event Start Time (leave blank for current time)"
    )

    def clean_actual_start_time(self):
        actual_start = self.cleaned_data.get('actual_start_time')
        if actual_start:
            now = timezone.now()
            if actual_start > now + datetime.timedelta(hours=1):
                raise ValidationError("Actual start time cannot be set into the future.")
        return actual_start


class EventCompletionForm(forms.Form):
    actual_end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=False,
        label="Actual Event End Time (leave blank for current time)"
    )
    completion_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional operational completion notes...'}),
        required=False,
        max_length=1000,
        label="Completion Notes"
    )
    incident_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any issues, facility damage, or operational incidents during event...'}),
        required=False,
        max_length=1000,
        label="Incident Notes"
    )

    def clean_actual_end_time(self):
        actual_end = self.cleaned_data.get('actual_end_time')
        if actual_end:
            now = timezone.now()
            if actual_end > now + datetime.timedelta(hours=1):
                raise ValidationError("Actual completion time cannot be set in the distant future.")
        return actual_end

    def clean_completion_notes(self):
        return (self.cleaned_data.get('completion_notes') or '').strip()

    def clean_incident_notes(self):
        return (self.cleaned_data.get('incident_notes') or '').strip()


class EventNoShowForm(forms.Form):
    no_show_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason or observation notes regarding participant no-show...'}),
        required=False,
        max_length=1000,
        label="No-Show Notes"
    )

    def clean_no_show_notes(self):
        return (self.cleaned_data.get('no_show_notes') or '').strip()
