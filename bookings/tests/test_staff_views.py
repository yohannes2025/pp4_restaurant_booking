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
from django.contrib.admin.views.decorators import staff_member_required


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
 
    def test_staff_table_edit_POST_success(self):
        response = self.client.post(
            reverse('staff_table_edit', args=[self.table1.pk]),
            data={'number': 99, 'capacity': 6}
        )
        self.assertRedirects(response, reverse('staff_table_list'))

        self.table1.refresh_from_db()
        self.assertEqual(self.table1.number, 99)
        self.assertEqual(self.table1.capacity, 6)

    def test_staff_dashboard_access(self):
        """
        Test access to staff dashboard for staff and non-staff users.
        """
        # Staff user access
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/staff_dashboard.html')
        self.assertIn('upcoming_active_bookings_count', response.context)
        self.assertIn('confirmed_today_count', response.context)
        self.assertIn('total_tables', response.context)

        # Non-staff user access (should be denied/redirected)
        self.client.logout()
        self.client.login(username='normaluser', password='password123')
        response = self.client.get(reverse('staff_dashboard'))

        # Redirect to login or permission denied
        self.assertEqual(response.status_code, 302)

        # The default behavior for staff_member_required is redirect to login if not authenticated        
        self.assertNotEqual(response.status_code, 200)

        # Unauthenticated user access
        self.client.logout()
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_staff_dashboard_counts(self):
        """
        Test the counts displayed on the staff dashboard.
        """
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)

        # upcoming_active_bookings_count: pending today, confirmed tomorrow
        self.assertEqual(response.context['upcoming_active_bookings_count'], 2)

        # confirmed_today_count: only bookings confirmed today (if any)
        self.assertEqual(response.context['confirmed_today_count'], 0)

        # Total tables
        self.assertEqual(
            response.context['total_tables'], Table.objects.count())

    def test_staff_booking_list_access(self):
        """
        Test access to staff booking list for staff and non-staff.
        """
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(reverse('staff_booking_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/staff_booking_list.html')
        self.assertIn('bookings', response.context)
        self.assertEqual(
            response.context['bookings'].paginator.count, Booking.objects.count())

        self.client.logout()
        self.client.login(username='normaluser', password='password123')
        response = self.client.get(reverse('staff_booking_list'))
        # Redirect due to @staff_member_required
        self.assertEqual(response.status_code, 302)

    def test_staff_booking_list_search_and_filters(self):
        """
        Test search and filter functionality on staff booking list.
        """
        self.client.login(username='staffuser', password='password123')

        # Search by username
        response = self.client.get(
            reverse('staff_booking_list'), {'q': 'normaluser'})
        # All bookings are by normaluser
        self.assertEqual(len(response.context['bookings']), 4)

        # Filter by status
        response = self.client.get(reverse('staff_booking_list'), {
                                   'status': 'confirmed'})
        self.assertEqual(len(response.context['bookings']), 1)
        self.assertEqual(
            response.context['bookings'][0], self.booking_tomorrow_confirmed)

        # Filter by date
        response = self.client.get(reverse('staff_booking_list'), {
                                   'date': self.today.isoformat()})
        self.assertEqual(len(response.context['bookings']), 1)
        self.assertEqual(
            response.context['bookings'][0], self.booking_today_pending)

        # Combined filters (tomorrow's confirmed booking)
        response = self.client.get(reverse('staff_booking_list'), {
            'q': 'normaluser',
            'status': 'confirmed',
            'date': self.tomorrow.isoformat()
        })
        self.assertEqual(len(response.context['bookings']), 1)
        self.assertEqual(
            response.context['bookings'][0], self.booking_tomorrow_confirmed)

        # Invalid date format
        response = self.client.get(reverse('staff_booking_list'), {
                                   'date': '2024-02-30'})  # Invalid date
        self.assertEqual(response.status_code, 200)  # Still renders page
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Invalid date format. Please use YYYY-MM-DD.")
        # date_filter should be reset
        self.assertFalse(response.context['date_filter'])
    
    def test_staff_booking_detail_GET(self):
        """
        Test GET request to staff booking detail view.
        """
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(reverse('staff_booking_detail', args=[
                                   self.booking_today_pending.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/staff_booking_detail.html')
        self.assertIn('booking', response.context)
        self.assertEqual(
            response.context['booking'], self.booking_today_pending)
        self.assertIn('form', response.context)  # Form for status update

    def test_staff_booking_detail_POST_update_status(self):
        """
        Test updating booking status from staff detail view.
        """
        self.client.login(username='staffuser', password='password123')
        initial_status = self.booking_today_pending.status
        form_data = {
            'status': 'confirmed',
            'notes': 'Confirmed by staff.'
        }
        response = self.client.post(
            reverse('staff_booking_detail', args=[
                    self.booking_today_pending.pk]),
            data=form_data,
            follow=True  # Follow redirect to get final response
        )
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('staff_booking_list'))
        self.booking_today_pending.refresh_from_db()
        self.assertEqual(self.booking_today_pending.status, 'confirmed')
        self.assertEqual(self.booking_today_pending.notes,
                         'Confirmed by staff.')
        self.assertContains(
            response, "Booking status updated successfully!", html=False)
    
    def test_staff_table_list_access(self):
        """
        Test access to staff table list for staff and non-staff.
        """
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(reverse('staff_table_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/staff_table_list.html')
        self.assertIn('tables', response.context)
        self.assertEqual(
            len(response.context['tables']), Table.objects.count())
        self.assertIn('form', response.context)  # Form for adding new tables

        self.client.logout()
        self.client.login(username='normaluser', password='password123')
        response = self.client.get(reverse('staff_table_list'))
        # Redirect due to @staff_member_required
        self.assertEqual(response.status_code, 302)

    def test_staff_table_list_POST_add_table(self):
        """
        Test POST request to add a new table from the staff table list view.
        """
        self.client.login(username='staffuser', password='password123')

        # Data for the new table with a unique number (e.g., 101)
        new_table_number = 101
        response = self.client.post(reverse('staff_table_list'), {
            'number': new_table_number,
            'capacity': 6
        }, follow=True)

        # Check that the response contains the success message
        self.assertContains(
            response, f"Table {new_table_number} added successfully!")

        # Verify that the new table exists in the database
        self.assertTrue(Table.objects.filter(number=new_table_number).exists())

    def test_staff_table_list_POST_add_table_duplicate_number(self):
        self.client.login(username='staffuser', password='password123')

        response = self.client.post(reverse('staff_table_list'), {
            'number': self.table1.number,  # duplicate number
            'capacity': 5
        }, follow=True)

        # <-- Add this line to debug the actual response content
        print(response.content.decode())

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response, "Table with this Number already exists.")
        self.assertContains(
            response, "Please correct the errors in the form when adding a table.")
        self.assertEqual(Table.objects.count(), 3)
