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

    