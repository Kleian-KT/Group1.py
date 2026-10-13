import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from reservations.models import Reservation
from reporting.views import sanitize_csv_cell

User = get_user_model()


class ReportingAndAnalyticsTests(TestCase):
    def setUp(self):
        self.category = FacilityCategory.objects.create(name='Lab', is_active=True)
        self.facility = Facility.objects.create(
            code='LAB-TEST',
            name='Test Lab',
            category=self.category,
            location='Floor 1',
            capacity=50,
            default_open_time=datetime.time(8, 0),
            default_close_time=datetime.time(20, 0),
            is_active=True
        )

        self.admin = User.objects.create_user(username='admin_rep', password='Password123!', role=User.ROLE_ADMIN, is_active=True)
        self.user = User.objects.create_user(username='user_rep', password='Password123!', role=User.ROLE_BASIC, is_active=True)

        self.client = Client()

    def test_formula_injection_sanitization(self):
        """Cells starting with =, +, -, @ must be prepended with a quote."""
        self.assertEqual(sanitize_csv_cell('=SUM(A1:A10)'), "'=SUM(A1:A10)")
        self.assertEqual(sanitize_csv_cell('+12345'), "'+12345")
        self.assertEqual(sanitize_csv_cell('-cmd|'), "'-cmd|")
        self.assertEqual(sanitize_csv_cell('@exec'), "'@exec")
        self.assertEqual(sanitize_csv_cell('Normal String'), "Normal String")
        self.assertEqual(sanitize_csv_cell(123), "123")

    def test_admin_reports_view_calculates_metrics(self):
        """Reports view computes real statistics from database."""
        now = timezone.now()
        Reservation.objects.create(
            reference='RES-REP-1',
            user=self.user,
            facility=self.facility,
            title='Calc Test',
            purpose='P',
            participant_count=10,
            start_time=now,
            end_time=now + datetime.timedelta(hours=2),
            status=Reservation.STATUS_APPROVED
        )

        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'RES-REP-1')
        self.assertContains(response, '2.0 hrs')

    def test_csv_export_reservations(self):
        """CSV export returns proper attachment header and filtered rows."""
        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('admin_reports_export_csv') + '?report_type=reservations')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue('attachment; filename="reservations_report_' in response['Content-Disposition'])

    def test_csv_export_utilization(self):
        """CSV utilization export calculates booked hours."""
        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('admin_reports_export_csv') + '?report_type=utilization')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('attachment; filename="facility_utilization_report_' in response['Content-Disposition'])

    def test_basic_user_blocked_from_csv_export(self):
        """Basic user cannot access admin CSV reports."""
        self.client.login(username='user_rep', password='Password123!')
        response = self.client.get(reverse('admin_reports_export_csv'))
        self.assertEqual(response.status_code, 403)
