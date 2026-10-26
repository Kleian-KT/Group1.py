import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from reservations.models import Reservation, ClosureBlock
from facilities.models import Facility
from audit_settings.models import SystemSetting


class ReservationSubmissionForm(forms.ModelForm):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Reservation
        fields = ['facility', 'title', 'purpose', 'participant_count', 'start_time', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Annual Student Assembly', 'minlength': '4', 'maxlength': '200'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide detailed purpose and schedule outline...', 'minlength': '10', 'maxlength': '2000'}),
            'participant_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise ValidationError("Event title is required.")
        if len(title) < 4:
            raise ValidationError("Event title must be at least 4 characters long.")
        if len(title) > 200:
            raise ValidationError("Event title cannot exceed 200 characters.")
        return title

    def clean_purpose(self):
        purpose = (self.cleaned_data.get('purpose') or '').strip()
        if not purpose:
            raise ValidationError("Event purpose is required.")
        if len(purpose) < 10:
            raise ValidationError("Event purpose must provide at least 10 characters detailing the activity outline.")
        if len(purpose) > 2000:
            raise ValidationError("Event purpose cannot exceed 2,000 characters.")
        return purpose

    def clean_participant_count(self):
        count = self.cleaned_data.get('participant_count')
        if count is None or count < 1:
            raise ValidationError("Participant count must be at least 1 person.")
        return count

    def clean(self):
        cleaned_data = super().clean()
        facility = cleaned_data.get('facility')
        participant_count = cleaned_data.get('participant_count')
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')

        if facility and participant_count:
            if participant_count > facility.capacity:
                self.add_error('participant_count', f"Participant count ({participant_count}) exceeds venue capacity ({facility.capacity}).")

        if start and end:
            if end <= start:
                self.add_error('end_time', "Reservation end time must be strictly after start time.")
            else:
                now = timezone.now()
                if start <= now:
                    self.add_error('start_time', "Reservation start time must be in the future.")

                if start.date() != end.date():
                    self.add_error('end_time', "Overnight reservations are not permitted. Reservation must be within a single day.")
                else:
                    max_duration_hours = SystemSetting.get_max_duration_hours()
                    duration_hours = (end - start).total_seconds() / 3600.0
                    if duration_hours > max_duration_hours:
                        self.add_error('end_time', f"Requested duration ({duration_hours:.1f} hrs) exceeds the maximum limit of {max_duration_hours} hours.")

                    max_advance_days = SystemSetting.get_max_advance_days()
                    advance_limit = (now + datetime.timedelta(days=max_advance_days)).date()
                    if start.date() > advance_limit:
                        self.add_error('start_time', f"Reservation date exceeds maximum advance booking limit of {max_advance_days} days.")

                    if facility:
                        booking_date = start.date()
                        is_closed, open_time, close_time = facility.get_operating_hours_for_date(booking_date)
                        if is_closed:
                            self.add_error('start_time', f"{facility.name} is closed on {booking_date.strftime('%A')}.")
                        elif open_time and close_time:
                            req_start_time = start.time()
                            req_end_time = end.time()
                            if req_start_time < open_time or req_end_time > close_time:
                                self.add_error(
                                    'start_time',
                                    f"Requested hours ({req_start_time.strftime('%H:%M')} - {req_end_time.strftime('%H:%M')}) "
                                    f"fall outside operating hours ({open_time.strftime('%H:%M')} - {close_time.strftime('%H:%M')})."
                                )

                        from reservations.services import get_overlapping_active_reservations, get_overlapping_closures
                        active_conflicts = get_overlapping_active_reservations(facility, start, end)
                        if self.instance and self.instance.pk:
                            active_conflicts = active_conflicts.exclude(pk=self.instance.pk)
                        if active_conflicts.exists():
                            self.add_error('start_time', "The requested schedule conflicts with an existing reservation hold or booking.")

                        closures = get_overlapping_closures(facility, start, end)
                        if closures.exists():
                            self.add_error('start_time', "The requested schedule conflicts with a scheduled facility closure.")

        return cleaned_data


class ReservationRejectForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide detailed administrative reason for rejection...', 'minlength': '5', 'maxlength': '500'}),
        required=True,
        label="Rejection Reason"
    )

    def clean_reason(self):
        reason = (self.cleaned_data.get('reason') or '').strip()
        if not reason:
            raise ValidationError("A rejection reason is mandatory.")
        if len(reason) < 5:
            raise ValidationError("Rejection reason must be at least 5 characters long.")
        if len(reason) > 500:
            raise ValidationError("Rejection reason cannot exceed 500 characters.")
        return reason


class ReservationRescheduleForm(forms.Form):
    new_start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'type': 'datetime-local'}),
        required=True,
        label="New Start Datetime"
    )
    new_end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'type': 'datetime-local'}),
        required=True,
        label="New End Datetime"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'rows': 3, 'placeholder': 'Administrative reason for rescheduling...', 'minlength': '5', 'maxlength': '500'}),
        required=True,
        label="Rescheduling Reason"
    )

    def clean_reason(self):
        reason = (self.cleaned_data.get('reason') or '').strip()
        if not reason:
            raise ValidationError("A rescheduling reason is mandatory.")
        if len(reason) < 5:
            raise ValidationError("Rescheduling reason must be at least 5 characters long.")
        if len(reason) > 500:
            raise ValidationError("Rescheduling reason cannot exceed 500 characters.")
        return reason

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('new_start_time')
        end = cleaned_data.get('new_end_time')
        if start and end:
            if end <= start:
                self.add_error('new_end_time', "New end datetime must be strictly after start datetime.")
            else:
                now = timezone.now()
                if start <= now:
                    self.add_error('new_start_time', "New start time must be in the future.")
                if start.date() != end.date():
                    self.add_error('new_end_time', "Overnight reservations are not permitted.")
                else:
                    max_duration_hours = SystemSetting.get_max_duration_hours()
                    duration_hours = (end - start).total_seconds() / 3600.0
                    if duration_hours > max_duration_hours:
                        self.add_error('new_end_time', f"Requested duration ({duration_hours:.1f} hrs) exceeds the maximum limit of {max_duration_hours} hours.")
        return cleaned_data


class ReservationAdminCancelForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Administrative reason for cancellation...', 'minlength': '5', 'maxlength': '500'}),
        required=True,
        label="Cancellation Reason"
    )

    def clean_reason(self):
        reason = (self.cleaned_data.get('reason') or '').strip()
        if not reason:
            raise ValidationError("A cancellation reason is mandatory.")
        if len(reason) < 5:
            raise ValidationError("Cancellation reason must be at least 5 characters long.")
        if len(reason) > 500:
            raise ValidationError("Cancellation reason cannot exceed 500 characters.")
        return reason


class ClosureBlockForm(forms.ModelForm):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select w-full rounded-lg border-slate-300 text-xs'})
    )

    class Meta:
        model = ClosureBlock
        fields = ['facility', 'start_time', 'end_time', 'reason']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'type': 'datetime-local'}),
            'reason': forms.Textarea(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'rows': 3, 'placeholder': 'e.g. Scheduled electrical maintenance and facility cleaning', 'minlength': '5', 'maxlength': '500'}),
        }

    def clean_reason(self):
        reason = (self.cleaned_data.get('reason') or '').strip()
        if not reason:
            raise ValidationError("A closure reason is mandatory.")
        if len(reason) < 5:
            raise ValidationError("Closure reason must be at least 5 characters long.")
        if len(reason) > 500:
            raise ValidationError("Closure reason cannot exceed 500 characters.")
        return reason

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', "Closure end datetime must be strictly after start datetime.")
        return cleaned_data
