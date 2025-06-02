from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from .models import Booking, Table
from .forms import BookingForm, AvailabilityForm, CustomUserCreationForm
from django.db.models import Q  # Import Q for complex queries
from django.contrib.auth import login
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger  # NEW IMPORT


def home_view(request):
    """Render the homepage."""
    return render(request, 'bookings/home.html')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log in the user after registration
            login(request, user)
            messages.success(request, "Registration successful. Welcome!")
            return redirect('home')  # Redirect to home page or a profile page
        else:
            # Add error messages to the form for display in template
            messages.error(
                request, "Registration failed. Please correct the errors below.")
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

            booking_datetime_naive = datetime.combine(
                booking_date, booking_time)
            booking_datetime = timezone.make_aware(booking_datetime_naive)

            if booking_datetime < timezone.now() - timedelta(minutes=1):
                messages.error(
                    request, "Booking date and time cannot be in the past.")
                return render(request, 'bookings/make_booking.html', {'form': form})

            # Find tables already booked at the exact date and time, excluding cancelled ones (FIX)
            booked_tables_ids = Booking.objects.filter(
                booking_date=booking_date,
                booking_time=booking_time
                # FIX: Exclude cancelled
            ).exclude(status='cancelled').values_list('table__id', flat=True)

            available_tables = Table.objects.filter(
                capacity__gte=number_of_guests
            ).exclude(id__in=booked_tables_ids).order_by('capacity')

            if available_tables.exists():
                selected_table = available_tables.first()
                try:
                    with transaction.atomic():
                        booking = form.save(commit=False)
                        booking.user = request.user
                        booking.table = selected_table
                        booking.status = 'pending'
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
def cancel_booking(request, booking_id):
    """Allow a user to cancel their booking."""
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
    """View to check table availability based on date, time, and guests."""
    available_tables = []
    if request.method == 'POST':
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            check_date = form.cleaned_data['check_date']
            check_time = form.cleaned_data['check_time']
            num_guests = form.cleaned_data['num_guests']

            # Find tables already booked at the exact date and time, excluding cancelled ones (FIX)
            booked_tables_ids = Booking.objects.filter(
                booking_date=check_date,
                booking_time=check_time
                # FIX: Exclude cancelled
            ).exclude(status='cancelled').values_list('table__id', flat=True)

            # Find tables that can accommodate the guests and are not booked
            available_tables = Table.objects.filter(
                capacity__gte=num_guests
            ).exclude(id__in=booked_tables_ids).order_by('capacity')

            if not available_tables.exists():
                messages.warning(
                    request, "No tables are available for the selected criteria.")
            else:
                messages.success(
                    request, f"Found {available_tables.count()} table(s) available.")
        else:
            messages.error(
                request, "Please correct the errors to check availability.")
    else:
        form = AvailabilityForm()

    context = {
        'form': form,
        'available_tables': available_tables,
    }
    return render(request, 'bookings/check_availability.html', context)


@staff_member_required  # Requires user to be logged in and is_staff=True
def staff_dashboard(request):
    """Restaurant staff dashboard overview."""

    today = timezone.now().date()

    now_time = timezone.now().time()

    # Upcoming bookings for today or future, that are pending or confirmed

    upcoming_active_bookings_count = Booking.objects.filter(

        Q(booking_date__gt=today) |  # Bookings in the future

        # Bookings today at or after current time
        Q(booking_date=today, booking_time__gte=now_time)

    ).filter(status__in=['pending', 'confirmed']).count()

    # Bookings confirmed for today

    confirmed_today_count = Booking.objects.filter(

        booking_date=today,

        status='confirmed'

    ).count()

    total_tables = Table.objects.count()

    context = {

        'upcoming_active_bookings_count': upcoming_active_bookings_count,

        'confirmed_today_count': confirmed_today_count,

        'total_tables': total_tables,

        'today': today,  # Pass today's date for filtering links in template

    }

    return render(request, 'bookings/staff_dashboard.html', context)


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
