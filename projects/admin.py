from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "last_updated_by", "updated_at")
    readonly_fields = ("created_by", "last_updated_by", "created_at", "updated_at")
