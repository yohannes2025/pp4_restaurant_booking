# bookings/tests/test_views.py
from datetime import time
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, time, timedelta, datetime
from django.utils import timezone
from bookings.models import Table, Booking
# For mocking timezone.now() if precise time control is needed
from unittest.mock import patch
from datetime import timedelta


User = get_user_model()


class PublicViewsTest(TestCase):
    """
    Tests for public views accessible to all users.
    """

    def setUp(self):
        self.client = Client()

    def test_home_view(self):
        """
        Test that the home view renders correctly.
        """
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/home.html')

    def test_register_view_GET(self):
        """
        Test that the register view renders the form on GET request.
        """
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        self.assertIn('form', response.context)

    def test_register_view_POST_success(self):
        """
        Test successful user registration and redirection.
        """
        initial_user_count = User.objects.count()
        response = self.client.post(reverse('register'), {
            'username': 'newuser_reg',
            'email': 'newuser_reg@example.com',
            'password1': 'SecureP@ss1',
            'password2': 'SecureP@ss1',
        })
        # Should redirect after login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        user = User.objects.get(username='newuser_reg')
        self.assertTrue(user.is_authenticated)  # User should be logged in

    def test_register_view_POST_failure(self):
        """
        Test failed user registration (e.g., password mismatch).
        """
        initial_user_count = User.objects.count()
        response = self.client.post(reverse('register'), {
            'username': 'failuser',
            'email': 'fail@example.com',
            'password1': 'pass1',
            'password2': 'pass2',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        self.assertIn('form', response.context)

        # Extract the form from the response context
        form = response.context['form']

        # Now assert the form error
        self.assertFormError(
            form, 'password2', "The two password fields didn’t match.")
        self.assertEqual(User.objects.count(), initial_user_count)
