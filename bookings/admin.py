from django.contrib import admin
from .models import Table, Booking


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'capacity')
    search_fields = ('number',)
    list_filter = ('capacity',)  # Added list_filter


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'table', 'booking_date', 'booking_time',
                    'number_of_guests', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'booking_date', 'booking_time', 'table__capacity')
    search_fields = ('user__username', 'table__number', 'notes')
    date_hierarchy = 'booking_date'
    # Allows changing status directly from the list view
    list_editable = ('status',)
    # Useful for large number of users/tables for better performance
    raw_id_fields = ('user', 'table',)
    # These fields are auto-managed
    readonly_fields = ('created_at', 'updated_at')
