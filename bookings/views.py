# bookings/views.py

from django.shortcuts import render

# Create your views here.


def home_view(request):
    """Render the homepage."""
    return render(request, 'bookings/home.html')
