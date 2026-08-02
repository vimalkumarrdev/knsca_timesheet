from django.conf import settings
from django.db import models

from projects.models import Project


class TimesheetEntry(models.Model):
    class WorkMode(models.TextChoices):
        WFO = "WFO", "Work From Office"
        WFH = "WFH", "Work From Home"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="timesheet_entries",
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="timesheet_entries",
    )
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    work_mode = models.CharField(max_length=3, choices=WorkMode.choices, default=WorkMode.WFO)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user} · {self.project} · {self.date}"


class OpenMonth(models.Model):
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
    )
    enabled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.year}-{self.month:02d}"
