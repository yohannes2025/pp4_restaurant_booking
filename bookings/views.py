from django.shortcuts import render
from django.contrib.auth.decorators import login_required  # Import the decorator


def home_view(request):
    """Render the homepage."""
    return render(request, 'bookings/home.html')

# Placeholder views for now, will be implemented later


@login_required
def make_booking(request):
    """Placeholder for booking creation."""
    return render(request, 'bookings/make_booking.html')


@login_required
def my_bookings(request):
    """Placeholder for displaying user's bookings."""
    return render(request, 'bookings/my_bookings.html')


@login_required
def cancel_booking(request, booking_id):
    """Placeholder for cancelling a booking."""
    return render(request, 'bookings/my_bookings.html')
