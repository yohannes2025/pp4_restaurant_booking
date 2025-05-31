# bookings/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # This will be your homepage for the bookings app
    # We will add more paths here later
    path('', views.home_view, name='home'),
]
