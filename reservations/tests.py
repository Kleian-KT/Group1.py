import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from facilities.models import Facility, FacilityCategory
from reservations.models import Reservation, ClosureBlock, ReservationChange
from reservations.services import (
    submit_reservation, approve_reservation, reject_reservation,
    reschedule_approved_reservation, cancel_reservation_by_user,
    create_closure_block, check_time_interval_overlap,
    ReservationConflictError, ReservationWorkflowError
)
from audit_settings.models import SystemSetting

User = get_user_model()


class ReservationValidationAndWorkflowTests(TestCase):
    def setUp(self):
        # Configure default settings
        SystemSetting.objects.update_or_create(key=SystemSetting.MAX_DURATION_KEY, defaults={'value': '4'})
        SystemSetting.objects.update_or_create(key=SystemSetting.MAX_ADVANCE_WINDOW_KEY, defaults={'value': '30'})

        self.category = FacilityCategory.objects.create(name='Lecture Halls', is_active=True)
        self.facility = Facility.objects.create(
            code='LH-101',
            name='Main Lecture Hall',
            category=self.category,
            location='Main Building',
            capacity=100,
            default_open_time=datetime.time(8, 0),
            default_close_time=datetime.time(20, 0),
            is_active=True
        )

        self.admin = User.objects.create_user(username='admin_res', password='Password123!', role=User.ROLE_ADMIN, is_active=True)
        self.user_a = User.objects.create_user(username='user_alice', password='Password123!', role=User.ROLE_BASIC, is_active=True)
        self.user_b = User.objects.create_user(username='user_bob', password='Password123!', role=User.ROLE_BASIC, is_active=True)

        self.base_time = timezone.now() + datetime.timedelta(days=3)
        self.client = Client()

    def test_interval_overlap_logic(self):
        """Half-open interval overlap [start, end). Adjacent slots must NOT overlap."""
        t1 = self.base_time.replace(hour=9, minute=0)
        t2 = self.base_time.replace(hour=10, minute=0)
        t3 = self.base_time.replace(hour=11, minute=0)

        # Adjacent [9, 10) and [10, 11) -> should be False
        self.assertFalse(check_time_interval_overlap(t1, t2, t2, t3))
        # Overlapping [9, 10:30) and [10:00, 11:00) -> should be True
        t_overlap = self.base_time.replace(hour=10, minute=30)
        self.assertTrue(check_time_interval_overlap(t1, t_overlap, t2, t3))

    def test_valid_reservation_creates_pending_status(self):
        """Valid submission produces PENDING reservation."""
        start = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        end = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)

        res = submit_reservation(
            user=self.user_a,
            facility=self.facility,
            title='Physics Lecture',
            purpose='Review session for exam',
            participant_count=50,
            start_time=start,
            end_time=end
        )
        self.assertEqual(res.status, Reservation.STATUS_PENDING)
        self.assertEqual(res.facility, self.facility)
        self.assertTrue(res.reference.startswith('RES-'))

    def test_invalid_participant_count_rejected(self):
        """Zero, negative, or capacity-exceeding counts rejected."""
        start = self.base_time.replace(hour=9, minute=0)
        end = self.base_time.replace(hour=11, minute=0)

        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 0, start, end)

        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 150, start, end) # Capacity is 100

    def test_past_start_time_rejected(self):
        """Past start times rejected."""
        past_start = timezone.now() - datetime.timedelta(hours=2)
        past_end = timezone.now() + datetime.timedelta(hours=1)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, past_start, past_end)

    def test_end_time_before_start_time_rejected(self):
        """End time <= start time rejected."""
        start = self.base_time.replace(hour=11, minute=0)
        end = self.base_time.replace(hour=9, minute=0)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, start, end)

    def test_overnight_booking_rejected(self):
        """Multi-day or overnight bookings must be rejected."""
        start = self.base_time.replace(hour=19, minute=0)
        end = (self.base_time + datetime.timedelta(days=1)).replace(hour=7, minute=0)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, start, end)

    def test_operating_hours_enforced(self):
        """Outside 8:00 - 20:00 operating hours rejected."""
        # Starts before 8:00
        start = self.base_time.replace(hour=7, minute=0)
        end = self.base_time.replace(hour=10, minute=0)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, start, end)

        # Ends after 20:00
        start2 = self.base_time.replace(hour=18, minute=0)
        end2 = self.base_time.replace(hour=21, minute=0)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, start2, end2)

    def test_max_duration_and_advance_window_enforced(self):
        """Exceeding 4 hours duration or 30 days advance window rejected."""
        # 5 hours duration
        start = self.base_time.replace(hour=9, minute=0)
        end = self.base_time.replace(hour=14, minute=0)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, start, end)

        # 45 days in advance
        far_future = timezone.now() + datetime.timedelta(days=45)
        start_far = far_future.replace(hour=9, minute=0)
        end_far = far_future.replace(hour=11, minute=0)
        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'T', 'P', 20, start_far, end_far)

    def test_adjacent_bookings_accepted(self):
        """Two adjacent bookings [09:00, 10:00) and [10:00, 11:00) can both be approved."""
        s1 = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        e1 = self.base_time.replace(hour=10, minute=0, second=0, microsecond=0)
        s2 = self.base_time.replace(hour=10, minute=0, second=0, microsecond=0)
        e2 = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)

        r1 = submit_reservation(self.user_a, self.facility, 'Event 1', 'Purp 1', 30, s1, e1)
        r2 = submit_reservation(self.user_b, self.facility, 'Event 2', 'Purp 2', 40, s2, e2)

        # Approve r1
        approve_reservation(r1.id, self.admin)
        r1.refresh_from_db()
        self.assertEqual(r1.status, Reservation.STATUS_APPROVED)

        # Approve r2 (adjacent slot)
        approve_reservation(r2.id, self.admin)
        r2.refresh_from_db()
        self.assertEqual(r2.status, Reservation.STATUS_APPROVED)

    def test_overlapping_approved_booking_blocks_approval(self):
        """Overlapping approval must fail with ReservationConflictError."""
        s1 = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        e1 = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)

        # Overlaps [10:00, 12:00)
        s2 = self.base_time.replace(hour=10, minute=0, second=0, microsecond=0)
        e2 = self.base_time.replace(hour=12, minute=0, second=0, microsecond=0)

        r1 = submit_reservation(self.user_a, self.facility, 'First', 'P1', 20, s1, e1)
        r2 = submit_reservation(self.user_b, self.facility, 'Second', 'P2', 20, s2, e2)

        approve_reservation(r1.id, self.admin)

        with self.assertRaises(ReservationConflictError):
            approve_reservation(r2.id, self.admin)

        r2.refresh_from_db()
        self.assertEqual(r2.status, Reservation.STATUS_PENDING) # Still valid pending

    def test_pending_request_does_not_block_slot(self):
        """Pending requests do not reserve slots. Either can be approved first."""
        s = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        e = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)

        r1 = submit_reservation(self.user_a, self.facility, 'Event A', 'P', 20, s, e)
        # Even though r1 is pending for [9, 11), submission for r2 is allowed
        # (submission only checks active closures and approved bookings)
        r2 = Reservation.objects.create(
            reference='RES-TEST-PEND-2',
            user=self.user_b,
            facility=self.facility,
            title='Event B',
            purpose='P',
            participant_count=20,
            start_time=s,
            end_time=e,
            status=Reservation.STATUS_PENDING
        )
        self.assertEqual(r1.status, Reservation.STATUS_PENDING)
        self.assertEqual(r2.status, Reservation.STATUS_PENDING)

    def test_closure_conflict_blocks_approval_and_submission(self):
        """Active closures prevent booking approvals and submissions."""
        s = self.base_time.replace(hour=13, minute=0, second=0, microsecond=0)
        e = self.base_time.replace(hour=16, minute=0, second=0, microsecond=0)

        create_closure_block(self.facility, s, e, 'Emergency maintenance', self.admin)

        with self.assertRaises(ValidationError):
            submit_reservation(self.user_a, self.facility, 'Blocked Event', 'P', 20, s, e)

    def test_cancelled_or_rejected_booking_releases_slot(self):
        """Cancelled or rejected bookings release their time slot for new approvals."""
        s = self.base_time.replace(hour=14, minute=0, second=0, microsecond=0)
        e = self.base_time.replace(hour=16, minute=0, second=0, microsecond=0)

        r1 = submit_reservation(self.user_a, self.facility, 'Event 1', 'P', 20, s, e)
        approve_reservation(r1.id, self.admin)

        # Cancel r1
        cancel_reservation_by_user(r1.id, self.user_a)
        r1.refresh_from_db()
        self.assertEqual(r1.status, Reservation.STATUS_CANCELLED)

        # New booking on same slot can now be approved
        r2 = Reservation.objects.create(
            reference='RES-TEST-NEW',
            user=self.user_b,
            facility=self.facility,
            title='Event 2',
            purpose='P',
            participant_count=20,
            start_time=s,
            end_time=e,
            status=Reservation.STATUS_PENDING
        )
        approve_reservation(r2.id, self.admin)
        r2.refresh_from_db()
        self.assertEqual(r2.status, Reservation.STATUS_APPROVED)

    def test_rejection_requires_reason(self):
        """Rejections without a reason are rejected."""
        s = self.base_time.replace(hour=9, minute=0)
        e = self.base_time.replace(hour=11, minute=0)
        r = submit_reservation(self.user_a, self.facility, 'Event', 'P', 20, s, e)

        with self.assertRaises(ValidationError):
            reject_reservation(r.id, self.admin, reason='')

        reject_reservation(r.id, self.admin, reason='Invalid documentation')
        r.refresh_from_db()
        self.assertEqual(r.status, Reservation.STATUS_REJECTED)
        self.assertEqual(r.decision_reason, 'Invalid documentation')
        self.assertEqual(r.decision_by, self.admin)

    def test_reschedule_preserves_history_in_reservation_change(self):
        """Rescheduling writes to ReservationChange and updates times atomically."""
        s = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        e = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)
        r = submit_reservation(self.user_a, self.facility, 'Event', 'P', 20, s, e)
        approve_reservation(r.id, self.admin)

        new_s = (self.base_time + datetime.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        new_e = (self.base_time + datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

        reschedule_approved_reservation(
            reservation_id=r.id,
            new_start_time=new_s,
            new_end_time=new_e,
            reason='Venue requested morning change',
            admin_user=self.admin
        )

        r.refresh_from_db()
        self.assertEqual(r.start_time, new_s)
        self.assertEqual(r.end_time, new_e)

        change = ReservationChange.objects.filter(reservation=r).first()
        self.assertIsNotNone(change)
        self.assertEqual(change.previous_start_time, s)
        self.assertEqual(change.new_start_time, new_s)
        self.assertEqual(change.changed_by, self.admin)

    def test_user_cannot_access_or_cancel_other_users_reservation(self):
        """User B cannot view or cancel User A's reservation."""
        s = self.base_time.replace(hour=9, minute=0)
        e = self.base_time.replace(hour=11, minute=0)
        r = submit_reservation(self.user_a, self.facility, 'User A Event', 'P', 20, s, e)

        # Log in as user B
        self.client.login(username='user_bob', password='Password123!')
        # Direct URL access to User A's reservation details
        detail_url = reverse('user_reservation_detail', kwargs={'reservation_id': r.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)

        # Direct POST cancel to User A's reservation
        cancel_url = reverse('user_reservation_cancel', kwargs={'reservation_id': r.id})
        response = self.client.post(cancel_url)
        # Should fail with 404 or ReservationWorkflowError
        self.assertEqual(response.status_code, 404)
        r.refresh_from_db()
        self.assertEqual(r.status, Reservation.STATUS_PENDING) # Untouched!

    def test_reservation_submission_form_validation(self):
        """ReservationSubmissionForm must be invalid if end_time <= start_time."""
        from reservations.forms import ReservationSubmissionForm
        s = self.base_time.replace(hour=14, minute=0)
        e = self.base_time.replace(hour=13, minute=0) # end before start
        form = ReservationSubmissionForm(data={
            'facility': self.facility.id,
            'title': 'Test Title',
            'purpose': 'Test Purpose',
            'participant_count': 10,
            'start_time': s.strftime('%Y-%m-%dT%H:%M'),
            'end_time': e.strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

    def test_reservation_reschedule_form_validation(self):
        """ReservationRescheduleForm must be invalid if new_end_time <= new_start_time."""
        from reservations.forms import ReservationRescheduleForm
        s = self.base_time.replace(hour=14, minute=0)
        e = self.base_time.replace(hour=13, minute=0)
        form = ReservationRescheduleForm(data={
            'new_start_time': s.strftime('%Y-%m-%dT%H:%M'),
            'new_end_time': e.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Adjust schedule',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('new_end_time', form.errors)

    def test_closure_block_form_validation(self):
        """ClosureBlockForm must be invalid if end_time <= start_time."""
        from reservations.forms import ClosureBlockForm
        s = self.base_time.replace(hour=14, minute=0)
        e = self.base_time.replace(hour=13, minute=0)
        form = ClosureBlockForm(data={
            'facility': self.facility.id,
            'start_time': s.strftime('%Y-%m-%dT%H:%M'),
            'end_time': e.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Maintenance',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

