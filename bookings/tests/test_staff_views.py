# bookings/tests/test_staff_views.py
from django.contrib.auth.models import User
from bookings.models import Table
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, time, timedelta, datetime
from django.utils import timezone
from bookings.models import Table, Booking
from bookings.models import Table

User = get_user_model()


def generate_unique_username(base='testuser'):
    return f"{base}_{uuid.uuid4().hex[:8]}"


class StaffViewsTest(TestCase):
    """
    Tests for staff-only views.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username='staffuser', password='password123', is_staff=True)
        cls.normal_user = User.objects.create_user(
            username='normaluser', password='password123')
        cls.table1 = Table.objects.create(number=10, capacity=4)
        cls.table2 = Table.objects.create(number=11, capacity=6)
        cls.today = timezone.now().date()
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.yesterday = cls.today - timedelta(days=1)

        # Create some bookings for testing staff views
        cls.booking_today_pending = Booking.objects.create(
            user=cls.normal_user, table=cls.table1,  # THIS IS THE KEY BOOKING FOR TABLE1
            booking_date=cls.today, booking_time=time(14, 0), number_of_guests=2, status='pending'
        )
        cls.booking_tomorrow_confirmed = Booking.objects.create(
            user=cls.normal_user, table=cls.table2,
            booking_date=cls.tomorrow, booking_time=time(19, 0), number_of_guests=4, status='confirmed'
        )
        cls.booking_yesterday_completed = Booking.objects.create(
            # Another booking on table1 (past, completed)
            user=cls.normal_user, table=cls.table1,
            booking_date=cls.yesterday, booking_time=time(12, 0), number_of_guests=2, status='completed'
        )
        cls.booking_future_cancelled = Booking.objects.create(
            # Another booking on table1 (future, cancelled)
            user=cls.normal_user, table=cls.table1,
            booking_date=cls.today + timedelta(days=5), booking_time=time(10, 0), number_of_guests=2, status='cancelled'
        )

    def setUp(self):
        # Create a staff user and log in
        self.staff_user = User.objects.create_user(
            username='teststaff',
            password='testpassword',
            is_staff=True
        )
        login_successful = self.client.login(
            username='teststaff',
            password='testpassword'
        )
        self.assertTrue(login_successful, "Login failed in setUp.")

        # Create a table with a unique number to avoid conflicts
        self.table = Table.objects.create(number=100, capacity=4)
