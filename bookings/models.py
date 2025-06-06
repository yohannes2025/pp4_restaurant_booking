from django.db import models
from django.contrib.auth.models import User  # Built-in user model
from datetime import date, time  # Used for potential custom logic


class Table(models.Model):
    number = models.IntegerField(unique=True, help_text="Unique table number.")
    capacity = models.IntegerField(
        help_text="Maximum number of guests this table can accommodate.")

    def __str__(self):
        return f"Table {self.number} (Capacity: {self.capacity})"


class Booking(models.Model):
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
        help_text="The user who made the booking."
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.PROTECT,
        related_name='bookings',
        help_text="The table reserved. Cannot be deleted if it has bookings."
    )
    booking_date = models.DateField(help_text="The date of the reservation.")
    booking_time = models.TimeField(help_text="The time of the reservation.")
    number_of_guests = models.IntegerField(
        help_text="Number of guests for the reservation.")
    notes = models.TextField(blank=True, null=True,
                             help_text="Optional special requests.")
    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS_CHOICES,
        default='pending',
        help_text="Current status of the booking."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when booking was created.")
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when booking was last updated.")

    class Meta:
        # Prevent double-booking a table
        unique_together = ('table', 'booking_date', 'booking_time')
        # Default sort order for queries
        ordering = ['booking_date', 'booking_time']

    def __str__(self):
        return f"Booking by {self.user.username} for Table {self.table.number} on {self.booking_date} at {self.booking_time} ({self.status})"
