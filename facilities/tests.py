import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from facilities.models import Facility, FacilityCategory, Amenity, FacilityAmenity, FacilityOperatingHour
from facilities.forms import (
    FacilityForm, FacilityCategoryForm, AmenityForm,
    FacilityAmenityForm, FacilityOperatingHourForm
)

User = get_user_model()


class FacilityFormsAndViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_fac',
            email='admin_fac@bulsu.edu.ph',
            first_name='Admin',
            last_name='Facilities',
            password='Password123!',
            role=User.ROLE_ADMIN,
            is_active=True
        )
        self.cat = FacilityCategory.objects.create(
            name='Auditoriums',
            description='Auditorium venues',
            is_active=True
        )
        self.fac = Facility.objects.create(
            code='VAL-TEST',
            name='Valencia Test Hall',
            category=self.cat,
            location='Main Campus',
            capacity=100,
            default_open_time=datetime.time(8, 0),
            default_close_time=datetime.time(20, 0),
            is_active=True
        )
        self.client = Client()

    def test_facility_form_valid(self):
        form = FacilityForm(data={
            'code': 'GYM-NEW',
            'name': 'New Gymnasium',
            'category': self.cat.id,
            'location': 'Gate 2',
            'capacity': 500,
            'default_open_time': '08:00',
            'default_close_time': '18:00',
            'is_active': True
        })
        self.assertTrue(form.is_valid(), form.errors)
        fac = form.save()
        self.assertEqual(fac.code, 'GYM-NEW')

    def test_facility_form_duplicate_code_rejected(self):
        form = FacilityForm(data={
            'code': 'val-test',  # lowercase duplicate
            'name': 'Different Name',
            'category': self.cat.id,
            'location': 'Gate 2',
            'capacity': 500,
            'default_open_time': '08:00',
            'default_close_time': '18:00',
            'is_active': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_facility_form_close_before_open_rejected(self):
        form = FacilityForm(data={
            'code': 'TST-TIME',
            'name': 'Time Test Hall',
            'category': self.cat.id,
            'location': 'Gate 1',
            'capacity': 100,
            'default_open_time': '18:00',
            'default_close_time': '08:00',
            'is_active': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('default_close_time', form.errors)

    def test_category_form_duplicate_rejected(self):
        form = FacilityCategoryForm(data={
            'name': 'auditoriums',  # case-insensitive
            'description': 'Duplicate test',
            'is_active': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_amenity_form_icon_validation(self):
        # Invalid icon
        form_bad = AmenityForm(data={
            'name': 'Projector A',
            'icon': 'bad_icon_format!!!',
            'is_active': True
        })
        self.assertFalse(form_bad.is_valid())
        self.assertIn('icon', form_bad.errors)

        # Valid icon
        form_good = AmenityForm(data={
            'name': 'Projector A',
            'icon': 'bi-projector',
            'is_active': True
        })
        self.assertTrue(form_good.is_valid())

    def test_operating_hours_form_when_closed_allows_empty_times(self):
        form = FacilityOperatingHourForm(data={
            'day_of_week': 6, # Sunday
            'is_closed': True,
            'open_time': '',
            'close_time': ''
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNotNone(form.cleaned_data['open_time'])
        self.assertIsNotNone(form.cleaned_data['close_time'])

    def test_operating_hours_form_when_open_requires_times(self):
        form = FacilityOperatingHourForm(data={
            'day_of_week': 1, # Tuesday
            'is_closed': False,
            'open_time': '',
            'close_time': ''
        })
        self.assertFalse(form.is_valid())
        self.assertIn('open_time', form.errors)
        self.assertIn('close_time', form.errors)

    def test_admin_facility_detail_renders_successfully(self):
        """Verify admin_facility_detail template renders without NoReverseMatch or errors."""
        self.client.login(username='admin_fac', password='Password123!')
        response = self.client.get(reverse('admin_facility_detail', kwargs={'facility_id': self.fac.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Valencia Test Hall')
        self.assertContains(response, 'Configure Day Operating Hours')
