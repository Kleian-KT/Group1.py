import datetime
import threading
from django.test import TransactionTestCase
from django.db import connection
from django.contrib.auth import get_user_model
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from reservations.models import Reservation
from reservations.services import (
    submit_reservation, approve_reservation,
    ReservationConflictError, ReservationWorkflowError
)
from audit_settings.models import SystemSetting

User = get_user_model()


class ConcurrentApprovalTests(TransactionTestCase):
    """
    Tests competing concurrent approval attempts for overlapping time slots.
    Uses TransactionTestCase to exercise true database transaction isolation and row locking.
    """
    reset_sequences = True

    def setUp(self):
        SystemSetting.objects.update_or_create(key=SystemSetting.MAX_DURATION_KEY, defaults={'value': '4'})
        SystemSetting.objects.update_or_create(key=SystemSetting.MAX_ADVANCE_WINDOW_KEY, defaults={'value': '30'})

        self.category = FacilityCategory.objects.create(name='Auditorium', is_active=True)
        self.facility = Facility.objects.create(
            code='CONC-AUD-1',
            name='Concurrency Hall',
            category=self.category,
            location='Engineering Center',
            capacity=200,
            default_open_time=datetime.time(8, 0),
            default_close_time=datetime.time(20, 0),
            is_active=True
        )

        self.admin1 = User.objects.create_user(username='admin_c1', password='Password123!', role=User.ROLE_ADMIN, is_active=True)
        self.admin2 = User.objects.create_user(username='admin_c2', password='Password123!', role=User.ROLE_ADMIN, is_active=True)
        self.user1 = User.objects.create_user(username='user_c1', password='Password123!', role=User.ROLE_BASIC, is_active=True)
        self.user2 = User.objects.create_user(username='user_c2', password='Password123!', role=User.ROLE_BASIC, is_active=True)

        self.target_date = timezone.now() + datetime.timedelta(days=4)
        self.slot_start = self.target_date.replace(hour=10, minute=0, second=0, microsecond=0)
        self.slot_end = self.target_date.replace(hour=12, minute=0, second=0, microsecond=0)

    def test_competing_concurrent_approvals_only_one_succeeds(self):
        """
        Two administrators simultaneously attempt to approve two different pending requests
        for the same facility and identical time slot.
        Only one must succeed; the loser must fail cleanly with ReservationConflictError.
        """
        # Create 2 pending reservations for the exact same slot
        res1 = Reservation.objects.create(
            reference='RES-CONC-001',
            user=self.user1,
            facility=self.facility,
            title='Department Concurrency Test 1',
            purpose='Testing atomic locks',
            participant_count=50,
            start_time=self.slot_start,
            end_time=self.slot_end,
            status=Reservation.STATUS_PENDING
        )

        res2 = Reservation.objects.create(
            reference='RES-CONC-002',
            user=self.user2,
            facility=self.facility,
            title='Department Concurrency Test 2',
            purpose='Testing atomic locks',
            participant_count=60,
            start_time=self.slot_start,
            end_time=self.slot_end,
            status=Reservation.STATUS_PENDING
        )

        results = {}
        errors = {}

        def attempt_approval(res_id, admin_user, thread_key):
            # Ensure fresh DB connection for the thread
            connection.close()
            try:
                approved_res = approve_reservation(res_id, admin_user)
                results[thread_key] = approved_res
            except Exception as e:
                errors[thread_key] = e
            finally:
                connection.close()

        t1 = threading.Thread(target=attempt_approval, args=(res1.id, self.admin1, 'thread_1'))
        t2 = threading.Thread(target=attempt_approval, args=(res2.id, self.admin2, 'thread_2'))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Reconnect main thread connection
        connection.close()

        # Verification:
        # Exactly one thread succeeded
        self.assertEqual(len(results), 1, f"Expected exactly 1 successful approval, got {len(results)}. Results: {results}, Errors: {errors}")
        # Exactly one thread caught a conflict error
        self.assertEqual(len(errors), 1, f"Expected exactly 1 conflict error, got {len(errors)}. Results: {results}, Errors: {errors}")

        # The error must be ReservationConflictError
        conflict_error = list(errors.values())[0]
        self.assertTrue(
            isinstance(conflict_error, (ReservationConflictError, ReservationWorkflowError)),
            f"Error was of unexpected type: {type(conflict_error)}"
        )

        # Check DB states
        res1.refresh_from_db()
        res2.refresh_from_db()

        statuses = [res1.status, res2.status]
        self.assertIn(Reservation.STATUS_APPROVED, statuses)
        self.assertIn(Reservation.STATUS_PENDING, statuses)

        # The approved one must have decision metadata
        approved_obj = res1 if res1.status == Reservation.STATUS_APPROVED else res2
        pending_obj = res2 if res1.status == Reservation.STATUS_APPROVED else res1

        self.assertIsNotNone(approved_obj.decision_by)
        self.assertIsNotNone(approved_obj.decision_at)

        # The losing pending one remains in a valid Pending state without corrupted metadata
        self.assertIsNone(pending_obj.decision_by)
        self.assertIsNone(pending_obj.decision_at)

    def test_serialized_concurrency_conflict_revalidation(self):
        """
        Validates that even if two approval requests pass initial checks simultaneously,
        revalidation inside the transaction.atomic block detects the newly committed approved booking.
        """
        res1 = Reservation.objects.create(
            reference='RES-SERIAL-001',
            user=self.user1,
            facility=self.facility,
            title='Serial Test 1',
            purpose='P',
            participant_count=30,
            start_time=self.slot_start,
            end_time=self.slot_end,
            status=Reservation.STATUS_PENDING
        )
        res2 = Reservation.objects.create(
            reference='RES-SERIAL-002',
            user=self.user2,
            facility=self.facility,
            title='Serial Test 2',
            purpose='P',
            participant_count=40,
            start_time=self.slot_start,
            end_time=self.slot_end,
            status=Reservation.STATUS_PENDING
        )

        # Approve res1
        approve_reservation(res1.id, self.admin1)
        res1.refresh_from_db()
        self.assertEqual(res1.status, Reservation.STATUS_APPROVED)

        # Attempt to approve res2 now -> Must raise ReservationConflictError
        with self.assertRaises(ReservationConflictError) as cm:
            approve_reservation(res2.id, self.admin2)

        self.assertIn('Conflict detected', str(cm.exception))
        res2.refresh_from_db()
        self.assertEqual(res2.status, Reservation.STATUS_PENDING)
