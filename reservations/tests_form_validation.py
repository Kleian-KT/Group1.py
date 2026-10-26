import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from facilities.models import Facility, FacilityCategory
from reservations.models import Reservation, ClosureBlock
from reservations.forms import (
    ReservationSubmissionForm, ReservationRejectForm,
    ReservationRescheduleForm, ReservationAdminCancelForm, ClosureBlockForm
)
from accounts.forms import UserRegistrationForm, UserProfileForm, AdminUserUpdateForm
from events.forms import EventCheckInForm, EventCompletionForm, EventNoShowForm
from audit_settings.forms import SystemSettingsForm
from audit_settings.models import SystemSetting

User = get_user_model()


class SystemWideFormValidationTests(TestCase):
    def setUp(self):
        SystemSetting.objects.update_or_create(
            key=SystemSetting.MAX_DURATION_KEY,
            defaults={'value': '4', 'description': 'Max duration'}
        )
        SystemSetting.objects.update_or_create(
            key=SystemSetting.MAX_ADVANCE_WINDOW_KEY,
            defaults={'value': '30', 'description': 'Max advance'}
        )
        self.user = User.objects.create_user(
            username='user_valid',
            email='valid_user@bulsu.edu.ph',
            first_name='Juan',
            last_name='Dela Cruz',
            phone_number='+63 917 111 2233',
            student_or_employee_id='2024-0001',
            password='Password123!',
            role=User.ROLE_BASIC,
            is_active=True
        )
        self.admin = User.objects.create_user(
            username='admin_valid',
            email='admin_valid@bulsu.edu.ph',
            first_name='Admin',
            last_name='User',
            password='Password123!',
            role=User.ROLE_ADMIN,
            is_active=True
        )
        self.category = FacilityCategory.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        self.facility = Facility.objects.create(
            code='VAL-AUD',
            name='Valencia Audio Hall',
            category=self.category,
            location='Main Campus Building A',
            capacity=50,
            default_open_time=datetime.time(8, 0),
            default_close_time=datetime.time(20, 0),
            is_active=True
        )

    # 1. Accounts Forms Validation Tests
    def test_user_registration_duplicate_email_rejected(self):
        form = UserRegistrationForm(data={
            'username': 'newuser123',
            'email': 'valid_user@bulsu.edu.ph',  # Existing email
            'first_name': 'Pedro',
            'last_name': 'Penduko',
            'phone_number': '+63 918 333 4455',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_user_registration_invalid_phone_rejected(self):
        form = UserRegistrationForm(data={
            'username': 'newuser124',
            'email': 'pedro@bulsu.edu.ph',
            'first_name': 'Pedro',
            'last_name': 'Penduko',
            'phone_number': 'not-a-phone-123',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)

    def test_user_registration_blank_or_short_name_rejected(self):
        form = UserRegistrationForm(data={
            'username': 'newuser125',
            'email': 'pedro2@bulsu.edu.ph',
            'first_name': 'A', # too short
            'last_name': '',  # empty
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)

    def test_user_profile_duplicate_email_rejected(self):
        # user tries to take admin's email
        form = UserProfileForm(instance=self.user, data={
            'first_name': 'Juan',
            'last_name': 'Dela Cruz',
            'email': 'admin_valid@bulsu.edu.ph',
            'phone_number': '+63 917 111 2233'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_admin_update_prevent_self_deactivation(self):
        form = AdminUserUpdateForm(instance=self.admin, current_user=self.admin, data={
            'first_name': 'Admin',
            'last_name': 'User',
            'email': 'admin_valid@bulsu.edu.ph',
            'role': User.ROLE_ADMIN,
            'is_active': False  # Self-deactivation attempt
        })
        self.assertFalse(form.is_valid())
        self.assertIn('is_active', form.errors)

    # 2. Reservation Submission Form Validation Tests
    def test_reservation_submission_short_title_and_purpose_rejected(self):
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        start = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        end = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(11, 0)))

        form = ReservationSubmissionForm(data={
            'facility': self.facility.id,
            'title': 'Hi', # < 4 chars
            'purpose': 'Short', # < 10 chars
            'participant_count': 10,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M')
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('purpose', form.errors)

    def test_reservation_submission_participant_exceeds_capacity_rejected(self):
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        start = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        end = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(11, 0)))

        # Facility capacity is 50, submitting 150
        form = ReservationSubmissionForm(data={
            'facility': self.facility.id,
            'title': 'Grand Assembly',
            'purpose': 'Meeting and presentations with faculty and students',
            'participant_count': 150,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M')
        })
        self.assertFalse(form.is_valid())
        self.assertIn('participant_count', form.errors)

    def test_reservation_submission_past_start_time_rejected(self):
        past_start = timezone.now() - datetime.timedelta(hours=2)
        past_end = past_start + datetime.timedelta(hours=1)

        form = ReservationSubmissionForm(data={
            'facility': self.facility.id,
            'title': 'Past Meeting',
            'purpose': 'Trying to book in the past for retro-records',
            'participant_count': 10,
            'start_time': past_start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': past_end.strftime('%Y-%m-%dT%H:%M')
        })
        self.assertFalse(form.is_valid())
        self.assertIn('start_time', form.errors)

    def test_reservation_submission_overnight_rejected(self):
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        day_after = tomorrow + datetime.timedelta(days=1)
        start = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(22, 0)))
        end = timezone.make_aware(datetime.datetime.combine(day_after, datetime.time(6, 0)))

        form = ReservationSubmissionForm(data={
            'facility': self.facility.id,
            'title': 'Overnight Hackathon',
            'purpose': 'Collaborative coding competition overnight event',
            'participant_count': 20,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M')
        })
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

    def test_reservation_submission_conflict_rejected(self):
        tomorrow = (timezone.now() + datetime.timedelta(days=2)).date()
        start = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10, 0)))
        end = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(12, 0)))

        # Create active approved reservation
        Reservation.objects.create(
            reference='RES-CONF-1',
            user=self.user,
            facility=self.facility,
            title='Existing Conflicting Event',
            purpose='Already approved event',
            participant_count=10,
            start_time=start,
            end_time=end,
            status=Reservation.STATUS_APPROVED
        )

        # Try to submit overlapping reservation
        overlap_start = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(11, 0)))
        overlap_end = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(13, 0)))

        form = ReservationSubmissionForm(data={
            'facility': self.facility.id,
            'title': 'New Conflicting Meeting',
            'purpose': 'Detailed purpose for new meeting request',
            'participant_count': 15,
            'start_time': overlap_start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': overlap_end.strftime('%Y-%m-%dT%H:%M')
        })
        self.assertFalse(form.is_valid())
        self.assertIn('start_time', form.errors)

    # 3. Administrative Forms Validation Tests
    def test_reservation_reject_form_empty_reason_rejected(self):
        form = ReservationRejectForm(data={'reason': '   '})
        self.assertFalse(form.is_valid())
        self.assertIn('reason', form.errors)

        form_valid = ReservationRejectForm(data={'reason': 'Venue undergoing maintenance during this window.'})
        self.assertTrue(form_valid.is_valid())

    def test_reservation_reschedule_form_validation(self):
        # End before start
        now = timezone.now() + datetime.timedelta(days=1)
        form_bad = ReservationRescheduleForm(data={
            'new_start_time': (now + datetime.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'new_end_time': now.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Adjusting time'
        })
        self.assertFalse(form_bad.is_valid())
        self.assertIn('new_end_time', form_bad.errors)

    def test_closure_form_validation(self):
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        start = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(15, 0)))
        end = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(12, 0)))

        form = ClosureBlockForm(data={
            'facility': self.facility.id,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Power shutdown'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

    # 4. Settings Form Validation Tests
    def test_system_settings_form_bounds(self):
        # Out of bounds duration (> 24)
        form_bad = SystemSettingsForm(data={
            'max_event_duration_hours': 36,
            'max_advance_booking_days': 30
        })
        self.assertFalse(form_bad.is_valid())
        self.assertIn('max_event_duration_hours', form_bad.errors)

        form_good = SystemSettingsForm(data={
            'max_event_duration_hours': 6,
            'max_advance_booking_days': 60
        })
        self.assertTrue(form_good.is_valid())
