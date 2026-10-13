from django import forms


class EventCheckInForm(forms.Form):
    actual_start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=False,
        label="Actual Event Start Time (leave blank for current time)"
    )


class EventCompletionForm(forms.Form):
    actual_end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=False,
        label="Actual Event End Time (leave blank for current time)"
    )
    completion_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional operational completion notes...'}),
        required=False,
        label="Completion Notes"
    )
    incident_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any issues, facility damage, or operational incidents during event...'}),
        required=False,
        label="Incident Notes"
    )


class EventNoShowForm(forms.Form):
    no_show_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason or observation notes regarding participant no-show...'}),
        required=False,
        label="No-Show Notes"
    )
