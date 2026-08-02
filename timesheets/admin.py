from django.contrib import admin

from .models import TimesheetEntry


@admin.register(TimesheetEntry)
class TimesheetEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "date", "hours")
    list_filter = ("project", "date")
