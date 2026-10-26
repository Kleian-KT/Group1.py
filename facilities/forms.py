import datetime
import re
from django import forms
from django.core.exceptions import ValidationError
from facilities.models import FacilityCategory, Facility, Amenity, FacilityAmenity, FacilityOperatingHour


class FacilityCategoryForm(forms.ModelForm):
    class Meta:
        model = FacilityCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'placeholder': 'e.g. Auditoriums & Theaters', 'minlength': '2'}),
            'description': forms.Textarea(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'rows': 3, 'placeholder': 'Category scope and classification notes'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input rounded text-bulsu-maroon focus:ring-bulsu-maroon'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise ValidationError("Category name is required.")
        if len(name) < 2:
            raise ValidationError("Category name must be at least 2 characters long.")
        if len(name) > 100:
            raise ValidationError("Category name cannot exceed 100 characters.")
        qs = FacilityCategory.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"A category named '{name}' already exists.")
        return name

    def clean_description(self):
        return (self.cleaned_data.get('description') or '').strip()


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ['code', 'name', 'category', 'location', 'capacity', 'description', 'default_open_time', 'default_close_time', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono uppercase', 'placeholder': 'e.g. AUD-101', 'minlength': '3', 'maxlength': '20'}),
            'name': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'placeholder': 'e.g. Main University Auditorium', 'minlength': '3'}),
            'category': forms.Select(attrs={'class': 'form-select w-full rounded-lg border-slate-300 text-xs'}),
            'location': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'placeholder': 'e.g. Federizo Hall, 2nd Floor', 'minlength': '3'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono font-bold', 'min': 1, 'max': 50000}),
            'description': forms.Textarea(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'rows': 3, 'placeholder': 'Usage guidelines, special policies, and access notes'}),
            'default_open_time': forms.TimeInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'type': 'time'}),
            'default_close_time': forms.TimeInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input rounded text-bulsu-maroon focus:ring-bulsu-maroon'}),
        }

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()
        if not code:
            raise ValidationError("Facility code is required.")
        if len(code) < 3:
            raise ValidationError("Facility code must be at least 3 characters long.")
        if len(code) > 20:
            raise ValidationError("Facility code cannot exceed 20 characters.")
        if not re.match(r'^[A-Z0-9_-]+$', code):
            raise ValidationError("Facility code can only contain uppercase letters, numbers, hyphens, and underscores (e.g. VAL-GYM).")
        qs = Facility.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Facility code '{code}' is already assigned to another facility.")
        return code

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise ValidationError("Facility name is required.")
        if len(name) < 3:
            raise ValidationError("Facility name must be at least 3 characters long.")
        if len(name) > 150:
            raise ValidationError("Facility name cannot exceed 150 characters.")
        qs = Facility.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"A facility with the name '{name}' already exists.")
        return name

    def clean_location(self):
        loc = (self.cleaned_data.get('location') or '').strip()
        if not loc:
            raise ValidationError("Location details are required.")
        if len(loc) < 3:
            raise ValidationError("Location must be at least 3 characters long.")
        return loc

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity is None or capacity < 1:
            raise ValidationError("Participant capacity must be at least 1 person.")
        if capacity > 50000:
            raise ValidationError("Participant capacity cannot exceed 50,000 for a university facility.")
        return capacity

    def clean_description(self):
        return (self.cleaned_data.get('description') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        open_time = cleaned_data.get('default_open_time')
        close_time = cleaned_data.get('default_close_time')
        if open_time and close_time:
            if close_time <= open_time:
                self.add_error('default_close_time', "Default closing time must be strictly after opening time.")
            else:
                diff_min = (close_time.hour * 60 + close_time.minute) - (open_time.hour * 60 + open_time.minute)
                if diff_min < 30:
                    self.add_error('default_close_time', "Facility operating window must be at least 30 minutes.")
        return cleaned_data


class AmenityForm(forms.ModelForm):
    class Meta:
        model = Amenity
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'placeholder': 'e.g. HD Laser Projector', 'minlength': '2'}),
            'description': forms.Textarea(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs', 'rows': 2, 'placeholder': 'Optional details and equipment specifications'}),
            'icon': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border-slate-300 text-xs font-mono', 'placeholder': 'e.g. bi-projector'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input rounded text-bulsu-maroon focus:ring-bulsu-maroon'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise ValidationError("Amenity name is required.")
        if len(name) < 2:
            raise ValidationError("Amenity name must be at least 2 characters long.")
        if len(name) > 100:
            raise ValidationError("Amenity name cannot exceed 100 characters.")
        qs = Amenity.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"An amenity named '{name}' already exists.")
        return name

    def clean_icon(self):
        icon = (self.cleaned_data.get('icon') or '').strip().lower()
        if not icon:
            return 'bi-check-circle'
        if not re.match(r'^bi-[a-z0-9-]+$', icon):
            raise ValidationError("Icon must follow Bootstrap Icons format (e.g. 'bi-projector', 'bi-mic', 'bi-wifi').")
        return icon

    def clean_description(self):
        return (self.cleaned_data.get('description') or '').strip()


class FacilityAmenityForm(forms.ModelForm):
    class Meta:
        model = FacilityAmenity
        fields = ['amenity', 'quantity', 'notes']
        widgets = {
            'amenity': forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 bg-white text-xs py-2 px-3 shadow-2xs focus:border-[#6b1414] focus:ring-1 focus:ring-[#6b1414] h-[38px]'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full h-full text-center font-mono font-bold text-slate-900 text-xs border-0 focus:ring-0 p-0 m-0 bg-transparent', 'min': 1, 'max': 1000, 'value': 1}),
            'notes': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-slate-300 bg-white text-xs py-2 px-3 shadow-2xs focus:border-[#6b1414] focus:ring-1 focus:ring-[#6b1414] h-[38px]', 'placeholder': 'Optional specifications or room location'}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None or qty < 1:
            raise ValidationError("Quantity must be at least 1.")
        if qty > 1000:
            raise ValidationError("Quantity cannot exceed 1,000 units.")
        return qty

    def clean_notes(self):
        return (self.cleaned_data.get('notes') or '').strip()


class FacilityOperatingHourForm(forms.ModelForm):
    open_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'w-full rounded-lg border border-slate-300 bg-white text-xs font-mono py-2 px-3 shadow-2xs focus:border-[#6b1414] focus:ring-1 focus:ring-[#6b1414] h-[38px]', 'type': 'time'})
    )
    close_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'w-full rounded-lg border border-slate-300 bg-white text-xs font-mono py-2 px-3 shadow-2xs focus:border-[#6b1414] focus:ring-1 focus:ring-[#6b1414] h-[38px]', 'type': 'time'})
    )

    class Meta:
        model = FacilityOperatingHour
        fields = ['day_of_week', 'open_time', 'close_time', 'is_closed']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 bg-white text-xs py-2 px-3 shadow-2xs focus:border-[#6b1414] focus:ring-1 focus:ring-[#6b1414] h-[38px]'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#6b1414] border-slate-300 focus:ring-[#6b1414] cursor-pointer'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_closed = cleaned_data.get('is_closed')
        open_time = cleaned_data.get('open_time')
        close_time = cleaned_data.get('close_time')

        if is_closed:
            # When closed, default times are populated if missing to satisfy model field requirements
            if not open_time:
                cleaned_data['open_time'] = datetime.time(8, 0)
            if not close_time:
                cleaned_data['close_time'] = datetime.time(17, 0)
        else:
            if not open_time:
                self.add_error('open_time', "Opening time is required when facility is open.")
            if not close_time:
                self.add_error('close_time', "Closing time is required when facility is open.")
            if open_time and close_time:
                if close_time <= open_time:
                    self.add_error('close_time', "Closing time must be strictly after opening time.")
                else:
                    diff_min = (close_time.hour * 60 + close_time.minute) - (open_time.hour * 60 + open_time.minute)
                    if diff_min < 30:
                        self.add_error('close_time', "Operating duration must be at least 30 minutes.")

        return cleaned_data
