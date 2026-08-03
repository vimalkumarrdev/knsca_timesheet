from django.contrib import admin

from .models import Claim, ClaimType


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("user", "claim_type", "from_date", "to_date", "amount", "status")
    list_filter = ("claim_type", "status")


@admin.register(ClaimType)
class ClaimTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
