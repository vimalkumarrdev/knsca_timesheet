from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role & Org", {"fields": ("role", "manager", "employee_code", "department", "date_joined_company")}),
    )
    list_display = ("username", "email", "role", "manager", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser")
