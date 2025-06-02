from django import forms
from .models import Booking, Table
from datetime import date, time, datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')



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

        if booking_date and booking_time:
            booking_datetime_naive = datetime.combine(
                booking_date, booking_time)
            booking_datetime = timezone.make_aware(booking_datetime_naive)

            if booking_datetime < timezone.now() - timedelta(minutes=1):
                self.add_error(
                    'booking_date', "Booking date and time cannot be in the past.")

            if not (time(9, 0) <= booking_time <= time(22, 0)):
                self.add_error(
                    'booking_time', "Booking time must be between 9:00 AM and 10:00 PM.")

        if number_of_guests is not None and number_of_guests <= 0:
            self.add_error('number_of_guests',
                           "Number of guests must be at least 1.")

        return cleaned_data


class AvailabilityForm(forms.Form):
    check_date = forms.DateField(
        label='Date',
        widget=forms.DateInput(
            attrs={'type': 'date', 'min': date.today().isoformat(), 'class': 'form-control'}),
        initial=date.today()
    )
    check_time = forms.TimeField(
        label='Time',
        widget=forms.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}),
        initial=time(19, 0)  # Default to 7 PM
    )
    num_guests = forms.IntegerField(
        label='Number of Guests',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        initial=2
    )

    def clean(self):
        cleaned_data = super().clean()
        check_date = cleaned_data.get('check_date')
        check_time = cleaned_data.get('check_time')
        num_guests = cleaned_data.get('num_guests')

        if check_date and check_time:
            # Make check_datetime timezone-aware for comparison (FIX)
            check_datetime_naive = datetime.combine(check_date, check_time)
            check_datetime = timezone.make_aware(
                check_datetime_naive)  # FIX: Make aware

            if check_datetime < timezone.now() - timedelta(minutes=1):
                raise forms.ValidationError(
                    "You cannot check availability for a past date and time.")

            if not (time(9, 0) <= check_time <= time(22, 0)):
                raise forms.ValidationError(
                    "Restaurant is open from 9:00 AM to 10:00 PM.")

        if num_guests is not None and num_guests <= 0:
            raise forms.ValidationError("Number of guests must be at least 1.")

        return cleaned_data


# Form for staff to update booking status

class BookingStatusUpdateForm(forms.ModelForm):

    class Meta:

        model = Booking

        fields = ['status', 'notes']  # Staff can update status and notes

        widgets = {

            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),

            # Use select for choices
            'status': forms.Select(attrs={'class': 'form-select'}),

        }

    labels = {

        'status': 'Booking Status',

        'notes': 'Staff Notes (Internal)',  # Clarify this is for staff

    }
