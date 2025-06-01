# Import redirect, get_object_or_404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta, date, time

from .models import Booking, Table
from .forms import BookingForm


def home_view(request):
    """Render the homepage."""
    return render(request, 'bookings/home.html')


@login_required
def make_booking(request):
    """Handle the booking creation form."""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking_date = form.cleaned_data['booking_date']
            booking_time = form.cleaned_data['booking_time']
            number_of_guests = form.cleaned_data['number_of_guests']

            # Make booking_datetime timezone-aware for comparison

            booking_datetime_naive = datetime.combine(
                booking_date, booking_time)

            booking_datetime = timezone.make_aware(
                booking_datetime_naive)  # FIX: Make aware

            # Basic check to prevent past bookings
            if booking_datetime < timezone.now() - timedelta(minutes=1):  # Allow current minute
                messages.error(
                    request, "Booking date and time cannot be in the past.")
                return render(request, 'bookings/make_booking.html', {'form': form})

            # Find tables already booked at the exact date and time            
            booked_tables_ids = Booking.objects.filter(
                booking_date=booking_date,
                booking_time=booking_time
            ).values_list('table__id', flat=True)

            # Find tables that can accommodate the guests and are not booked
            available_tables = Table.objects.filter(
                capacity__gte=number_of_guests
            ).exclude(id__in=booked_tables_ids).order_by('capacity')

            if available_tables.exists():
                # For simplicity, assign to the smallest available table that fits
                selected_table = available_tables.first()
                try:
                    with transaction.atomic():  # Ensure atomicity for booking creation
                        booking = form.save(commit=False)
                        booking.user = request.user
                        booking.table = selected_table
                        booking.status = 'pending'  # Default new bookings to pending
                        booking.save()
                        messages.success(
                            request, f"Your booking for Table {selected_table.number} has been confirmed!")
                        # Redirect to user's bookings
                        return redirect('my_bookings')
                except Exception as e:
                    messages.error(
                        request, f"An error occurred during booking: {e}")
            else:
                messages.warning(
                    request, "No tables available for your requested date, time, and number of guests.")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = BookingForm()  # Initialize empty form for GET request
    return render(request, 'bookings/make_booking.html', {'form': form})


@login_required
def my_bookings(request):
    """Placeholder for displaying user's bookings."""
    # Will be implemented later
    return render(request, 'bookings/my_bookings.html')


@login_required
def cancel_booking(request, booking_id):
    """Placeholder for cancelling a booking."""
    # Will be implemented later
    return render(request, 'bookings/my_bookings.html')
