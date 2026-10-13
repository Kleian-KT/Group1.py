from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthenticationAndPermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_test',
            password='Password123!',
            role=User.ROLE_ADMIN,
            is_active=True
        )
        self.user_a = User.objects.create_user(
            username='user_a',
            password='Password123!',
            role=User.ROLE_BASIC,
            is_active=True
        )
        self.user_b = User.objects.create_user(
            username='user_b',
            password='Password123!',
            role=User.ROLE_BASIC,
            is_active=True
        )
        self.client = Client()

    def test_registration_creates_basic_user_only(self):
        """Verify that basic registration cannot escalate or assign ADMIN role."""
        response = self.client.post(reverse('register'), {
            'username': 'attacker',
            'email': 'attacker@campus.edu',
            'first_name': 'Hacker',
            'last_name': 'Attempt',
            'password': 'ComplexPassword123!',
            'password_confirm': 'ComplexPassword123!',
            'role': User.ROLE_ADMIN,  # Tampered field
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='attacker')
        self.assertEqual(new_user.role, User.ROLE_BASIC)
        self.assertFalse(new_user.is_admin_role())

    def test_role_based_redirect_after_login(self):
        """Admin redirects to /manage/, Basic User redirects to /portal/."""
        # Admin login
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.get(reverse('login_redirect'), follow=False)
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.client.logout()

        # Basic user login
        self.client.login(username='user_a', password='Password123!')
        response = self.client.get(reverse('login_redirect'), follow=False)
        self.assertRedirects(response, reverse('user_dashboard'))

    def test_unauthenticated_cannot_access_protected_pages(self):
        """Unauthenticated user redirected to login."""
        endpoints = [
            reverse('admin_dashboard'),
            reverse('admin_user_list'),
            reverse('user_dashboard'),
            reverse('user_reservation_list'),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse('login')))

    def test_basic_user_cannot_access_admin_pages(self):
        """Basic user gets 403 PermissionDenied or is blocked from admin pages."""
        self.client.login(username='user_a', password='Password123!')
        admin_urls = [
            reverse('admin_dashboard'),
            reverse('admin_user_list'),
            reverse('admin_settings'),
            reverse('admin_reports'),
            reverse('admin_audit_logs'),
        ]
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_deactivated_user_cannot_login_or_perform_transactions(self):
        """Deactivated accounts cannot sign in and are actively logged out by middleware."""
        self.user_a.is_active = False
        self.user_a.save()

        # Attempt login
        response = self.client.post(reverse('login'), {
            'username': 'user_a',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 200) # Re-rendered with error message
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_active_user_deactivated_mid_session_is_expelled(self):
        """If user is deactivated mid-session, middleware logs them out immediately."""
        self.client.login(username='user_a', password='Password123!')
        # Deactivate user in DB
        self.user_a.is_active = False
        self.user_a.save()

        # Next request should trigger middleware logout & redirect
        response = self.client.get(reverse('user_dashboard'))
        self.assertRedirects(response, reverse('login'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        # Subsequent attempts are fully unauthenticated
        subsequent = self.client.get(reverse('user_dashboard'))
        self.assertRedirects(subsequent, reverse('login'))
