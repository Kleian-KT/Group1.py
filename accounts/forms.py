import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()

# Robust validation regexes
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
NAME_PATTERN = re.compile(r"^[a-zA-Z\s\.\-'\ñ\Ñ]+$")
PHONE_PATTERN = re.compile(r'^(\+63|0)9\d{9}$|^(\+63|0)[2-8]\d{7}$|^\+?[0-9\s\-\(\)]{7,20}$')


def validate_clean_name(value, field_name="Name"):
    val = (value or '').strip()
    if not val:
        raise ValidationError(f"{field_name} is required.")
    if len(val) < 2:
        raise ValidationError(f"{field_name} must be at least 2 characters long.")
    if len(val) > 50:
        raise ValidationError(f"{field_name} cannot exceed 50 characters.")
    if not NAME_PATTERN.match(val):
        raise ValidationError(f"{field_name} can only contain letters, spaces, hyphens, and periods.")
    return val


def validate_clean_phone(phone_raw):
    phone = (phone_raw or '').strip()
    if not phone:
        return ""
    digits = re.sub(r'[\s\-\(\)\+]', '', phone)
    if len(digits) < 7 or not PHONE_PATTERN.match(phone):
        raise ValidationError("Please enter a valid phone number (e.g. +63 912 345 6789 or 09123456789).")
    return phone


def validate_unique_email(email_raw, current_pk=None):
    email = (email_raw or '').strip().lower()
    if not email:
        raise ValidationError("Email address is required.")
    qs = User.objects.filter(email__iexact=email)
    if current_pk:
        qs = qs.exclude(pk=current_pk)
    if qs.exists():
        raise ValidationError("An account with this email address already exists.")
    return email


def validate_unique_student_id(sid_raw, current_pk=None):
    sid = (sid_raw or '').strip()
    if not sid:
        return ""
    if len(sid) < 3:
        raise ValidationError("Student/Employee ID must be at least 3 characters long.")
    if len(sid) > 50:
        raise ValidationError("Student/Employee ID cannot exceed 50 characters.")
    qs = User.objects.filter(student_or_employee_id__iexact=sid)
    if current_pk:
        qs = qs.exclude(pk=current_pk)
    if qs.exists():
        raise ValidationError("This Student / Employee ID is already registered to another user.")
    return sid


class UserRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name', 'minlength': '2'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name', 'minlength': '2'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create password', 'minlength': '8'}),
        validators=[validate_password]
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password', 'minlength': '8'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'department', 'student_or_employee_id']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. jdelacruz', 'minlength': '3'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. juan@bulsu.edu.ph'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63 912 345 6789'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. College of Information and Communications Technology'}),
            'student_or_employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2024-101001'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        if len(username) > 30:
            raise ValidationError("Username cannot exceed 30 characters.")
        if not USERNAME_PATTERN.match(username):
            raise ValidationError("Username can only contain alphanumeric characters, dots, underscores, and hyphens.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        return validate_unique_email(self.cleaned_data.get('email'))

    def clean_first_name(self):
        return validate_clean_name(self.cleaned_data.get('first_name'), "First name")

    def clean_last_name(self):
        return validate_clean_name(self.cleaned_data.get('last_name'), "Last name")

    def clean_phone_number(self):
        return validate_clean_phone(self.cleaned_data.get('phone_number'))

    def clean_student_or_employee_id(self):
        return validate_unique_student_id(self.cleaned_data.get('student_or_employee_id'))

    def clean_department(self):
        return (self.cleaned_data.get('department') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_BASIC
        user.is_active = True
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'minlength': '2'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'minlength': '2'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'department', 'student_or_employee_id']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63 912 345 6789'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'student_or_employee_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_first_name(self):
        return validate_clean_name(self.cleaned_data.get('first_name'), "First name")

    def clean_last_name(self):
        return validate_clean_name(self.cleaned_data.get('last_name'), "Last name")

    def clean_email(self):
        return validate_unique_email(self.cleaned_data.get('email'), current_pk=self.instance.pk if self.instance else None)

    def clean_phone_number(self):
        return validate_clean_phone(self.cleaned_data.get('phone_number'))

    def clean_student_or_employee_id(self):
        return validate_unique_student_id(self.cleaned_data.get('student_or_employee_id'), current_pk=self.instance.pk if self.instance else None)

    def clean_department(self):
        return (self.cleaned_data.get('department') or '').strip()


class AdminUserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'minlength': '2'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'minlength': '2'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'is_active', 'phone_number', 'department', 'student_or_employee_id']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'student_or_employee_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_first_name(self):
        return validate_clean_name(self.cleaned_data.get('first_name'), "First name")

    def clean_last_name(self):
        return validate_clean_name(self.cleaned_data.get('last_name'), "Last name")

    def clean_email(self):
        return validate_unique_email(self.cleaned_data.get('email'), current_pk=self.instance.pk if self.instance else None)

    def clean_phone_number(self):
        return validate_clean_phone(self.cleaned_data.get('phone_number'))

    def clean_student_or_employee_id(self):
        return validate_unique_student_id(self.cleaned_data.get('student_or_employee_id'), current_pk=self.instance.pk if self.instance else None)

    def clean_department(self):
        return (self.cleaned_data.get('department') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.current_user and self.instance == self.current_user:
            is_active = cleaned_data.get('is_active')
            role = cleaned_data.get('role')
            if is_active is False:
                self.add_error('is_active', "Security violation: Administrators cannot deactivate their own account.")
            if role and role != User.ROLE_ADMIN:
                self.add_error('role', "Security violation: Administrators cannot revoke their own administrator privileges.")
        return cleaned_data
