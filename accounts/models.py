from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        MANAGER = "MANAGER", "Manager"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)
    manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="team_members", limit_choices_to={"role": Role.MANAGER},
    )
    employee_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=50, blank=True)
    date_joined_company = models.DateField(null=True, blank=True)

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
