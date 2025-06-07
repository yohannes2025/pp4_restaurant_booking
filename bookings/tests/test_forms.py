# bookings/tests/test_forms.py
from django.test import TestCase
from django import forms
from datetime import date, time, timedelta, datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from bookings.forms import (
    CustomUserCreationForm,
    BookingForm,
    AvailabilityForm,
    BookingStatusUpdateForm,
    TableForm
)
from bookings.models import Booking, Table

User = get_user_model()


class CustomUserCreationFormTest(TestCase):
    """
    Tests for the CustomUserCreationForm.
    """

    def test_valid_form(self):
        form = CustomUserCreationForm(data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongP@ssw0rd',
            'password2': 'StrongP@ssw0rd',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertTrue(user.check_password('StrongP@ssw0rd'))

    def test_password_mismatch(self):
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'password123',
            'password2': 'differentpassword',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password fields", form.errors["password2"][0])

    def test_duplicate_username(self):
        User.objects.create_user(username='existinguser', password='password')
        form = CustomUserCreationForm(data={
            'username': 'existinguser',
            'email': 'some@example.com',
            'password1': 'pass',
            'password2': 'pass',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn("A user with that username already exists.",
                      form.errors['username'])
