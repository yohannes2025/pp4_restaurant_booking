# Standard library imports
from datetime import datetime, timedelta, time

# Third-party imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

# Local application imports
from .models import Booking, Table
from .forms import (
    BookingForm,
    AvailabilityForm,
    BookingStatusUpdateForm,
    TableForm,
    CustomUserCreationForm,
)



def home_view(request):
    """Render the homepage."""
    return render(request, 'bookings/home.html')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # FIX: Set backend explicitly
            user.backend = 'django.contrib.auth.backends.ModelBackend'

            login(request, user)
            messages.success(request, "Registration successful. Welcome!")
            return redirect('home')
        else:
            messages.error(
                request, "Registration failed. Please correct the errors below.")
            return render(request, 'registration/register.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def make_booking(request):
    """Handle the booking creation form."""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking_date = form.cleaned_data['booking_date']
            booking_time = form.cleaned_data['booking_time']
            number_of_guests = form.cleaned_data['number_of_guests']

            # Combine date and time, then make it timezone-aware
            booking_datetime = datetime.combine(booking_date, booking_time)
            booking_datetime = timezone.make_aware(booking_datetime)

            # Define allowed time range
            opening_time = time(9, 0)   # 9:00 AM
            closing_time = time(22, 0)  # 10:00 PM

            # Check if booking time is outside of allowed interval
            if not (opening_time <= booking_time <= closing_time):
                messages.warning(
                    request, "Bookings can only be made between 9:00 AM and 10:00 PM.")
                return render(request, 'bookings/make_booking.html', {'form': form})

            # Check if the booking is in the past
            if booking_datetime < timezone.now():
                form.add_error(
                    'booking_date', "Booking date cannot be in the past.")
                return render(request, 'bookings/make_booking.html', {'form': form})

            # Find tables booked at the exact time
            booked_tables_ids = Booking.objects.filter(
                booking_date=booking_date,
                booking_time=booking_time
            ).values_list('table__id', flat=True)

            # Start with tables that match capacity and aren't booked at that exact time
            available_tables = Table.objects.filter(
                capacity__gte=number_of_guests
            ).exclude(id__in=booked_tables_ids)

            # Further exclude tables booked within 1 hour window
            one_hour_before = (datetime.combine(
                booking_date, booking_time) - timedelta(hours=1)).time()
            one_hour_after = (datetime.combine(
                booking_date, booking_time) + timedelta(hours=1)).time()

            conflicting_bookings = Booking.objects.filter(
                booking_date=booking_date,
                table__in=available_tables,
                booking_time__range=(one_hour_before, one_hour_after)
            )

            conflicting_table_ids = conflicting_bookings.values_list(
                'table__id', flat=True)
            available_tables = available_tables.exclude(
                id__in=conflicting_table_ids).order_by('capacity')

            if available_tables.exists():
                selected_table = available_tables.first()
                try:
                    with transaction.atomic():
                        booking = form.save(commit=False)
                        booking.user = request.user
                        booking.table = selected_table
                        booking.status = 'confirmed'
                        booking.save()
                        messages.success(
                            request, f"Your booking for Table {selected_table.number} has been confirmed!")
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
        form = BookingForm()
    return render(request, 'bookings/make_booking.html', {'form': form})


@login_required
def my_bookings(request):
    """Display a list of the current user's bookings."""
    # Upcoming bookings: date is today or in the future, and not cancelled/completed
    upcoming_bookings = Booking.objects.filter(
        user=request.user,
        booking_date__gte=timezone.now().date()
    ).exclude(status__in=['cancelled', 'no-show', 'completed']).order_by('booking_date', 'booking_time')

    # Past bookings: date is in the past, or date is today but time is in the past
    past_bookings = Booking.objects.filter(
        user=request.user
    ).filter(
        Q(booking_date__lt=timezone.now().date()) |  # Date is in the past
        # Or date is today and time is in the past
        Q(booking_date=timezone.now().date(),
          booking_time__lt=timezone.now().time())
        # Order by most recent past booking first
    ).order_by('-booking_date', '-booking_time')

    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
    }
    return render(request, 'bookings/my_bookings.html', context)


@login_required
def edit_booking(request, booking_id):
    """Allow a user to edit his/her existing booking."""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            booking_date = form.cleaned_data['booking_date']
            booking_time = form.cleaned_data['booking_time']
            number_of_guests = form.cleaned_data['number_of_guests']

            # Combine date and time, then make it timezone-aware
            booking_datetime = datetime.combine(booking_date, booking_time)
            booking_datetime = timezone.make_aware(booking_datetime)

            # Define allowed time range (same as in make_booking)
            opening_time = time(9, 0)
            closing_time = time(22, 0)

            # Check if booking time is outside of allowed interval
            if not (opening_time <= booking_time <= closing_time):
                messages.warning(
                    request, "Bookings can only be made between 9:00 AM and 10:00 PM.")
                return render(request, 'bookings/edit_booking.html', {'form': form, 'booking': booking})

            # Check if the booking is in the past
            if booking_datetime < timezone.now():
                messages.warning(
                    request, "You cannot edit a booking to a past time.")
                return render(request, 'bookings/edit_booking.html', {'form': form, 'booking': booking})

            # Find tables booked at the exact time, excluding the current booking's table
            booked_tables_ids = Booking.objects.filter(
                booking_date=booking_date,
                booking_time=booking_time
            ).exclude(id=booking.id).values_list('table__id', flat=True)

            # Start with tables that match capacity and aren't booked at that exact time
            available_tables = Table.objects.filter(
                capacity__gte=number_of_guests
            ).exclude(id__in=booked_tables_ids)

            # Further exclude tables booked within 1 hour window, excluding the current booking's table
            one_hour_before = (datetime.combine(
                booking_date, booking_time) - timedelta(hours=1)).time()
            one_hour_after = (datetime.combine(
                booking_date, booking_time) + timedelta(hours=1)).time()

            conflicting_bookings = Booking.objects.filter(
                booking_date=booking_date,
                table__in=available_tables,
                booking_time__range=(one_hour_before, one_hour_after)
            ).exclude(id=booking.id)  # Exclude the current booking itself

            conflicting_table_ids = conflicting_bookings.values_list(
                'table__id', flat=True)
            available_tables = available_tables.exclude(
                id__in=conflicting_table_ids).order_by('capacity')

            if available_tables.exists():
                selected_table = available_tables.first()
                try:
                    with transaction.atomic():
                        # Update the existing booking with new data
                        booking.booking_date = booking_date
                        booking.booking_time = booking_time
                        booking.number_of_guests = number_of_guests
                        booking.table = selected_table  # Assign the newly found table
                        booking.save()
                        messages.success(
                            request, f"Your booking for Table {selected_table.number} has been updated successfully!")
                        return redirect('my_bookings')
                except Exception as e:
                    messages.error(
                        request, f"An error occurred during booking update: {e}")
            else:
                messages.warning(
                    request, "No tables available for your requested date, time, and number of guests for this edit.")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = BookingForm(instance=booking)

    context = {
        'form': form,
        'booking': booking,
    }
    return render(request, 'bookings/edit_booking.html', context)


@login_required
def cancel_booking(request, booking_id):
    """Allow a user to cancel his/her booking."""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Prevent cancellation if the booking is too close to the time (e.g., within 2 hours)
    booking_datetime_naive = datetime.combine(
        booking.booking_date, booking.booking_time)
    booking_datetime = timezone.make_aware(
        booking_datetime_naive)  # Ensure timezone awareness

    if booking_datetime < timezone.now() + timedelta(hours=2):
        messages.error(
            request, "Bookings cannot be cancelled within 2 hours of the reservation time.")
    # Prevent cancelling already finalized bookings
    elif booking.status in ['cancelled', 'completed', 'no-show']:
        messages.warning(
            request, f"This booking is already {booking.get_status_display()}. Cannot cancel.")
    else:
        booking.status = 'cancelled'  # Soft delete: set status to cancelled
        booking.save()
        messages.success(
            request, "Your booking has been successfully cancelled.")

    return redirect('my_bookings')


def check_availability(request):
    """View to check table availability based on date, time, and guests, enforcing a ±2 hour rule."""
    available_tables = []

    if request.method == 'POST':
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            check_date = form.cleaned_data['check_date']
            check_time = form.cleaned_data['check_time']
            num_guests = form.cleaned_data['num_guests']

            # Combine date and time into a datetime object
            requested_datetime = timezone.make_aware(
                datetime.combine(check_date, check_time))
            two_hours_before = (requested_datetime - timedelta(hours=2)).time()
            two_hours_after = (requested_datetime + timedelta(hours=2)).time()

            # Find conflicting bookings within ±2 hours on the same date
            conflicting_bookings = Booking.objects.filter(
                booking_date=check_date,
                booking_time__range=(two_hours_before, two_hours_after),
                status='confirmed'  # Only confirmed bookings block availability
            )

            conflicting_table_ids = conflicting_bookings.values_list(
                'table_id', flat=True)

            # Find available tables that meet guest count and are not conflicted
            available_tables = Table.objects.filter(
                capacity__gte=num_guests
            ).exclude(id__in=conflicting_table_ids).order_by('capacity')

            if not available_tables.exists():
                messages.warning(
                    request, "No tables are available within 2 hours of the selected time.")
            else:
                messages.success(
                    request, f"Found {available_tables.count()} table(s) available.")
        else:
            messages.error(
                request, "Please correct the errors to check availability.")
    else:
        form = AvailabilityForm()

    return render(request, 'bookings/check_availability.html', {
        'form': form,
        'available_tables': available_tables
    })


def staff_dashboard(request):
    # Ensure only staff can access
    if not request.user.is_staff:
        # Redirect or show permission denied as appropriate
        return redirect('login')  # or use permission decorators

    today = timezone.now().date()

    # Filter bookings with status 'pending' or 'confirmed' and date >= today
    upcoming_bookings = Booking.objects.filter(
        booking_date__gte=today,
        status__in=['pending', 'confirmed']
    )

    # Count the number of upcoming active bookings
    upcoming_active_bookings_count = upcoming_bookings.count()

    # Count bookings confirmed for today (optional, based on your context)
    confirmed_today_count = Booking.objects.filter(
        booking_date=today,
        status='confirmed'
    ).count()

    total_tables = Table.objects.count()

    context = {
        'upcoming_active_bookings_count': upcoming_active_bookings_count,
        'confirmed_today_count': confirmed_today_count,
        'total_tables': total_tables,
    }

    return render(request, 'bookings/staff_dashboard.html', context)

# Decorator for staff members (assuming you have this defined elsewhere or use is_staff check)


# Staff Booking List View

@staff_member_required
def staff_booking_list(request):
    """List all bookings for staff, with search and filters."""

    bookings_list = Booking.objects.all().order_by(
        '-booking_date', '-booking_time')  # Get all bookings

    query = request.GET.get('q')  # Search query

    status_filter = request.GET.get('status')  # Status filter

    date_filter = request.GET.get('date')  # Date filter

    if query:

        bookings_list = bookings_list.filter(

            Q(user__username__icontains=query) |

            Q(table__number__icontains=query) |

            Q(notes__icontains=query)

        )

    if status_filter:

        bookings_list = bookings_list.filter(status=status_filter)

    if date_filter:

        try:

            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()

            bookings_list = bookings_list.filter(booking_date=parsed_date)

        except ValueError:

            messages.error(
                request, "Invalid date format. Please use YYYY-MM-DD.")

            date_filter = None  # Reset date_filter to avoid pre-filling invalid value

    # Implement pagination

    paginator = Paginator(bookings_list, 10)  # Show 10 bookings per page

    page = request.GET.get('page')

    try:

        bookings = paginator.page(page)

    except PageNotAnInteger:

        bookings = paginator.page(1)

    except EmptyPage:

        bookings = paginator.page(paginator.num_pages)

    context = {

        'bookings': bookings,

        'query': query,

        'status_filter': status_filter,

        'date_filter': date_filter,

        # Pass choices to template for dropdown
        'status_choices': Booking.BOOKING_STATUS_CHOICES,

    }

    return render(request, 'bookings/staff_booking_list.html', context)


# Staff Booking Detail View

@staff_member_required
def staff_booking_detail(request, booking_id):
    """View and update details of a specific booking."""

    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':

        form = BookingStatusUpdateForm(
            request.POST, instance=booking)  # Use the new form

        if form.is_valid():

            form.save()

            messages.success(request, "Booking status updated successfully!")

            return redirect('staff_booking_list')

        else:

            messages.error(
                request, "Error updating booking status. Please correct the errors.")

    else:

        # Initialize form with existing data
        form = BookingStatusUpdateForm(instance=booking)

    context = {

        'booking': booking,

        'form': form,  # Pass the form to the template

    }

    return render(request, 'bookings/staff_booking_detail.html', context)


# Staff Table List View

@staff_member_required
def staff_table_list(request):
    """
    Displays a list of all restaurant tables and allows staff to add new ones.
    """
    tables = Table.objects.all().order_by('number')

    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"Table {form.cleaned_data['number']} added successfully!")
            return redirect('staff_table_list')
        else:
            messages.error(
                request, "Please correct the errors in the form when adding a table.")
    else:
        form = TableForm()  # For GET request, provide an empty form

    context = {
        'tables': tables,
        'form': form,
        'active_tab': 'tables',
    }
    return render(request, 'bookings/staff_table_list.html', context)

# Staff Table Edit View

@staff_member_required
def staff_table_edit(request, table_id):
    """Edit an existing table."""

    table = get_object_or_404(Table, id=table_id)  # Get the specific table

    if request.method == 'POST':

        # Populate form with POST data and instance
        form = TableForm(request.POST, instance=table)

        if form.is_valid():

            form.save()

            messages.success(
                request, f"Table {table.number} updated successfully!")

            return redirect('staff_table_list')  # Redirect back to list

        else:

            messages.error(
                request, "Error updating table. Please check the form.")

    else:

        # Populate form with existing table data for GET request
        form = TableForm(instance=table)

    context = {

        'form': form,

        'table': table,  # Pass table object to template

    }

    return render(request, 'bookings/staff_table_edit.html', context)


# Staff Table Delete View

@staff_member_required
def staff_table_delete(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    if request.method == 'POST':
        # Check for active bookings
        active_bookings = Booking.objects.filter(
            table=table,
            status__in=['confirmed', 'pending']  # or your actual active statuses
        )

        if active_bookings.exists():
            # Do NOT delete; set error message
            messages.error(
                request,
                f"Cannot delete table {table.number} because it has active bookings."
            )
            return redirect('staff_table_list')

        # No active bookings, safe to delete
        try:
            table.delete()
            messages.success(
                request, f"Table {table.number} deleted successfully."
            )
        except Exception as e:
            messages.error(
                request, f"Error deleting table {table.number}: {e}"
            )

        return redirect('staff_table_list')
    else:
        # For GET or other methods, show warning
        messages.warning(
            request, "Invalid request to delete table. Please delete via POST."
        )
        return redirect('staff_table_list')
