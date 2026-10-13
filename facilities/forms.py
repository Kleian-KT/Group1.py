from django import forms
from facilities.models import FacilityCategory, Facility, Amenity, FacilityAmenity, FacilityOperatingHour


class FacilityCategoryForm(forms.ModelForm):
    class Meta:
        model = FacilityCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Auditorium'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Category description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ['code', 'name', 'category', 'location', 'capacity', 'description', 'default_open_time', 'default_close_time', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AUD-101'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main University Auditorium'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Building A, 2nd Floor'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'default_open_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'default_close_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        open_time = cleaned_data.get('default_open_time')
        close_time = cleaned_data.get('default_close_time')
        if open_time and close_time and close_time <= open_time:
            self.add_error('default_close_time', "Default closing time must be strictly after opening time.")
        return cleaned_data


class AmenityForm(forms.ModelForm):
    class Meta:
        model = Amenity
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HD Projector'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. bi-projector'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FacilityAmenityForm(forms.ModelForm):
    class Meta:
        model = FacilityAmenity
        fields = ['amenity', 'quantity', 'notes']
        widgets = {
            'amenity': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional specifications or location in room'}),
        }


class FacilityOperatingHourForm(forms.ModelForm):
    class Meta:
        model = FacilityOperatingHour
        fields = ['day_of_week', 'open_time', 'close_time', 'is_closed']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'open_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_closed = cleaned_data.get('is_closed')
        open_time = cleaned_data.get('open_time')
        close_time = cleaned_data.get('close_time')
        if not is_closed and open_time and close_time and close_time <= open_time:
            self.add_error('close_time', "Closing time must be after opening time.")
        return cleaned_data
