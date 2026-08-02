from django.conf import settings
from django.db import models


class Claim(models.Model):
    class ClaimType(models.TextChoices):
        MOBILE_BILL = "MOBILE_BILL", "Mobile Bill"
        INTERNET_BILL = "INTERNET_BILL", "Internet Bill"
        PETROL_ALLOWANCE = "PETROL_ALLOWANCE", "Petrol Allowance"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="claims",
    )
    claim_type = models.CharField(max_length=20, choices=ClaimType.choices)
    from_date = models.DateField()
    to_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bill_copy = models.FileField(upload_to="claim_bills/%Y/%m/")
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_claims",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.get_claim_type_display()} · {self.from_date} to {self.to_date}"
