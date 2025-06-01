from django import forms
from .models import Booking
from datetime import date, time, datetime, timedelta  # Import datetime, timedelta
from django.utils import timezone  # Import timezone


class BookingForm(forms.ModelForm):
    booking_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'min': date.today().isoformat(), 'class': 'form-control'}),
        initial=date.today(),
        label='Preferred Date'
    )
    booking_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}),
        label='Preferred Time'
    )
    number_of_guests = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        initial=2,
        label='Number of Guests'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label='Special Requests/Notes'
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'number_of_guests', 'notes']

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time = cleaned_data.get('booking_time')
        number_of_guests = cleaned_data.get('number_of_guests')

        # Validate date and time
        if booking_date and booking_time:
            # Make booking_datetime timezone-aware for comparison
            booking_datetime_naive = datetime.combine(
                booking_date, booking_time)
            booking_datetime = timezone.make_aware(booking_datetime_naive)

            # Prevent booking in the past (allow current minute for immediate bookings)
            if booking_datetime < timezone.now() - timedelta(minutes=1):
                self.add_error(
                    'booking_date', "Booking date and time cannot be in the past.")

            # Restaurant opening hours validation (9 AM to 10 PM)
            # Time objects themselves are naive, comparison is fine.
            if not (time(9, 0) <= booking_time <= time(22, 0)):
                self.add_error(
                    'booking_time', "Booking time must be between 9:00 AM and 10:00 PM.")

        # Validate number of guests
        if number_of_guests is not None and number_of_guests <= 0:
            self.add_error('number_of_guests',
                           "Number of guests must be at least 1.")

        return cleaned_data
