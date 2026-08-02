from django.contrib import admin

from .models import OpenMonth, TimesheetEntry


@admin.register(TimesheetEntry)
class TimesheetEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "date", "hours")
    list_filter = ("project", "date")


@admin.register(OpenMonth)
class OpenMonthAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "enabled_by", "enabled_at")
