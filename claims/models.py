from django.conf import settings
from django.db import models

from projects.models import Project


class ClaimType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    bill_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class SettlementStatus(models.TextChoices):
        NOT_SETTLED = "NOT_SETTLED", "Not Settled"
        SETTLED = "SETTLED", "Settled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="claims",
    )
    claim_type = models.ForeignKey(
        ClaimType, on_delete=models.PROTECT, related_name="claims",
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="claims",
    )
    from_date = models.DateField()
    to_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bill_copy = models.FileField(upload_to="claim_bills/%Y/%m/", blank=True, null=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_claims",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    settlement_status = models.CharField(
        max_length=15, choices=SettlementStatus.choices, default=SettlementStatus.NOT_SETTLED,
    )
    settled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="settled_claims",
    )
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.claim_type} · {self.from_date} to {self.to_date}"
