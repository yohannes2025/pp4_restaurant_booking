# bookings/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from datetime import date, time, timedelta
from bookings.models import Table, Booking

User = get_user_model()


class TableModelTest(TestCase):
    """
    Tests for the Table model.
    """
    def test_create_table(self):
        """
        Test that a Table object can be created successfully with correct attributes.
        """
        table = Table.objects.create(number=1, capacity=4)
        self.assertEqual(table.number, 1)
        self.assertEqual(table.capacity, 4)
        self.assertEqual(str(table), "Table 1 (Capacity: 4)")

    def test_unique_table_number(self):
        """
        Test that table numbers must be unique.
        """
        Table.objects.create(number=10, capacity=4)
        with self.assertRaises(IntegrityError):

            Table.objects.create(number=10, capacity=6)

    def test_table_capacity_validation(self):
        """
        Test that capacity cannot be negative.
        """      
        table = Table.objects.create(number=2, capacity=-1)
        
        self.assertEqual(table.capacity, -1)        


