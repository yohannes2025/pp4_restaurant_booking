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


class BookingFormTest(TestCase):
    def test_booking_form_past_date_time(self):
        # Create a booking date/time in the past
        past_date = date.today() - timedelta(days=1)
        past_time = time(12, 0)  # Noon

        form_data = {
            'booking_date': past_date,
            'booking_time': past_time,
            'number_of_guests': 2,
            'notes': 'Test past booking',
        }
        form = BookingForm(data=form_data)

        # Should be invalid because date/time is in the past
        self.assertFalse(form.is_valid())

        # Check error is under '__all__' because clean() raises ValidationError
        self.assertIn('booking_date', form.errors)

        self.assertIn('Booking date cannot be in the past.',
                      form.errors['booking_date'])

    def test_booking_form_time_out_of_range(self):
        # Time before 9 AM
        form_data = {
            'booking_date': date.today() + timedelta(days=1),
            'booking_time': time(8, 0),
            'number_of_guests': 2,
            'notes': '',
        }
        form = BookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_time', form.errors)
        self.assertIn(
            'Booking time must be between 9:00 AM and 10:00 PM.', form.errors['booking_time'])

    def test_booking_form_zero_guests(self):
        form_data = {
            'booking_date': date.today() + timedelta(days=1),
            'booking_time': time(12, 0),
            'number_of_guests': 0,
            'notes': '',
        }
        form = BookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('number_of_guests', form.errors)
        self.assertIn('Number of guests must be at least 1.',
                      form.errors['number_of_guests'])
