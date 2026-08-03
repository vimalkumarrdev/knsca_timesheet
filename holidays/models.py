from django.conf import settings
from django.db import models


class Holiday(models.Model):
    class HolidayType(models.TextChoices):
        COMPANY = "COMPANY", "Company Holiday"
        GOVERNMENT = "GOVERNMENT", "Government Holiday"

    date = models.DateField()
    name = models.CharField(max_length=150)
    holiday_type = models.CharField(
        max_length=20, choices=HolidayType.choices, default=HolidayType.COMPANY,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="holidays_added",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.name} ({self.date})"
