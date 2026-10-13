from django import forms
from reservations.models import Reservation, ClosureBlock
from facilities.models import Facility


class ReservationSubmissionForm(forms.ModelForm):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Reservation
        fields = ['facility', 'title', 'purpose', 'participant_count', 'start_time', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Annual Student Assembly'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide detailed purpose and schedule outline...'}),
            'participant_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', "Reservation end time must be strictly after start time.")
        return cleaned_data


class ReservationRejectForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide detailed administrative reason for rejection...'}),
        required=True,
        label="Rejection Reason"
    )


class ReservationRescheduleForm(forms.Form):
    new_start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=True,
        label="New Start Datetime"
    )
    new_end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=True,
        label="New End Datetime"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Administrative reason for rescheduling...'}),
        required=True,
        label="Rescheduling Reason"
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('new_start_time')
        end = cleaned_data.get('new_end_time')
        if start and end and end <= start:
            self.add_error('new_end_time', "New end datetime must be strictly after start datetime.")
        return cleaned_data


class ReservationAdminCancelForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Administrative reason for cancellation...'}),
        required=True,
        label="Cancellation Reason"
    )


class ClosureBlockForm(forms.ModelForm):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = ClosureBlock
        fields = ['facility', 'start_time', 'end_time', 'reason']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g. Scheduled electrical maintenance and facility cleaning'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', "Closure end datetime must be strictly after start datetime.")
        return cleaned_data
