from django import forms
from .models import Booking
from datetime import date, time  # Will be used for initial values and validation


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
        required=False,  # Make notes optional
        label='Special Requests/Notes'
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'number_of_guests', 'notes']
