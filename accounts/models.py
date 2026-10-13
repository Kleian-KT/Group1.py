from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_BASIC = 'BASIC_USER'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = (
        (ROLE_BASIC, 'Basic User'),
        (ROLE_ADMIN, 'Admin'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_BASIC,
        help_text="Application-level role: BASIC USER or ADMIN"
    )
    phone_number = models.CharField(max_length=30, blank=True)
    department = models.CharField(max_length=100, blank=True)
    student_or_employee_id = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN

    def is_basic_role(self):
        return self.role == self.ROLE_BASIC

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"
