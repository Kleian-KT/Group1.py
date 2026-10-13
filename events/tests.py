import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from facilities.models import Facility, FacilityCategory
from reservations.models import Reservation
from events.models import EventRecord
from reservations.services import (
    submit_reservation, approve_reservation, check_in_event,
    complete_event, mark_event_no_show, ReservationWorkflowError
)

User = get_user_model()


class EventOperationsTests(TestCase):
    def setUp(self):
        self.category = FacilityCategory.objects.create(name='Hall', is_active=True)
        self.facility = Facility.objects.create(
            code='HALL-1',
            name='Campus Hall',
            category=self.category,
            location='Main Campus',
            capacity=80,
            default_open_time=datetime.time(8, 0),
            default_close_time=datetime.time(20, 0),
            is_active=True
        )
        self.admin = User.objects.create_user(username='admin_ev', password='Password123!', role=User.ROLE_ADMIN, is_active=True)
        self.user = User.objects.create_user(username='user_ev', password='Password123!', role=User.ROLE_BASIC, is_active=True)

        self.base_time = timezone.now() + datetime.timedelta(days=2)
        self.client = Client()

    def test_check_in_permitted_only_from_approved_state(self):
        """Cannot check in a Pending reservation."""
        start = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        end = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)
        res = submit_reservation(self.user, self.facility, 'Event', 'P', 20, start, end)

        # Pending -> Cannot check in
        with self.assertRaises(ReservationWorkflowError):
            check_in_event(res.id, self.admin)

        # Approve -> Now check-in succeeds
        approve_reservation(res.id, self.admin)
        ev_rec = check_in_event(res.id, self.admin)
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_CHECKED_IN)
        self.assertIsNotNone(ev_rec.check_in_time)

    def test_completion_permitted_only_after_check_in(self):
        """Cannot complete without check-in first."""
        start = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        end = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)
        res = submit_reservation(self.user, self.facility, 'Event', 'P', 20, start, end)
        approve_reservation(res.id, self.admin)

        with self.assertRaises(ReservationWorkflowError):
            complete_event(res.id, self.admin)

        # Check in first
        check_in_event(res.id, self.admin)
        # Complete
        complete_event(res.id, self.admin, incident_notes='None', completion_notes='Clean')
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_COMPLETED)
        self.assertEqual(res.event_record.completion_notes, 'Clean')

    def test_actual_end_time_cannot_precede_actual_start_time(self):
        """Invalid end time preceding start time raises ValidationError."""
        start = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        end = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)
        res = submit_reservation(self.user, self.facility, 'Event', 'P', 20, start, end)
        approve_reservation(res.id, self.admin)

        act_start = start.replace(hour=9, minute=15)
        check_in_event(res.id, self.admin, actual_start_time=act_start)

        # Attempt to end at 9:00 (before start 9:15)
        act_end_invalid = start.replace(hour=9, minute=0)
        with self.assertRaises(ValidationError):
            complete_event(res.id, self.admin, actual_end_time=act_end_invalid)

    def test_no_show_permitted_only_after_scheduled_end_time(self):
        """No Show can only be recorded after end time has elapsed."""
        # Future event
        start = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        end = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)
        res = submit_reservation(self.user, self.facility, 'Future Event', 'P', 20, start, end)
        approve_reservation(res.id, self.admin)

        # End time has not passed yet
        with self.assertRaises(ReservationWorkflowError):
            mark_event_no_show(res.id, self.admin)

        # Past event whose end time elapsed
        past_start = timezone.now() - datetime.timedelta(hours=5)
        past_end = timezone.now() - datetime.timedelta(hours=3)
        res_past = Reservation.objects.create(
            reference='RES-PAST-1',
            user=self.user,
            facility=self.facility,
            title='Past Event',
            purpose='P',
            participant_count=10,
            start_time=past_start,
            end_time=past_end,
            status=Reservation.STATUS_APPROVED
        )

        mark_event_no_show(res_past.id, self.admin, no_show_notes='Did not show up')
        res_past.refresh_from_db()
        self.assertEqual(res_past.status, Reservation.STATUS_NO_SHOW)
        self.assertEqual(res_past.event_record.no_show_notes, 'Did not show up')

    def test_printable_reservation_slip_view(self):
        """Printable slip loads properly and renders reservation reference."""
        start = self.base_time.replace(hour=9, minute=0, second=0, microsecond=0)
        end = self.base_time.replace(hour=11, minute=0, second=0, microsecond=0)
        res = submit_reservation(self.user, self.facility, 'Printable Event', 'P', 20, start, end)
        approve_reservation(res.id, self.admin)

        self.client.login(username='admin_ev', password='Password123!')
        url = reverse('admin_event_print_slip', kwargs={'reservation_id': res.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, res.reference)
        self.assertContains(response, 'Official Facility Reservation Slip')
