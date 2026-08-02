from django.conf import settings
from django.db import models

from projects.models import Project


class TimesheetEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="timesheet_entries",
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="timesheet_entries",
    )
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user} · {self.project} · {self.date}"
