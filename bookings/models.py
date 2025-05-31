from django.db import models


class Table(models.Model):
    """Represents a restaurant table."""
    number = models.IntegerField(unique=True, help_text="Unique table number.")
    capacity = models.IntegerField(
        help_text="Maximum number of guests this table can accommodate.")

    def __str__(self):
        return f"Table {self.number} (Capacity: {self.capacity})"
