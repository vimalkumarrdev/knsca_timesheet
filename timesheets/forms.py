import calendar
from datetime import date

from django import forms

from holidays.models import Holiday
from leaves.models import Leave
from projects.models import Client, Project

from .models import OpenMonth, TimesheetEntry


class TimesheetEntryForm(forms.ModelForm):
    client = forms.ModelChoiceField(queryset=Client.objects.order_by("name"), required=True, label="Client")

    class Meta:
        model = TimesheetEntry
        fields = ["client", "project", "date", "hours", "work_mode", "remarks"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0", "max": "24"}),
            "work_mode": forms.RadioSelect(),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Optional notes…"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["client"].empty_label = "Select Client"
        self.fields["project"].queryset = Project.objects.select_related("client").filter(client__isnull=False).order_by("name")
        self.fields["project"].empty_label = "Select Project"

        if self.instance and self.instance.pk and self.instance.project_id:
            self.fields["client"].initial = self.instance.project.client_id

        today = date.today()
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        earliest_open = OpenMonth.objects.order_by("year", "month").first()
        if earliest_open:
            min_date = date(earliest_open.year, earliest_open.month, 1)
        else:
            min_date = today.replace(day=1)

        self.fields["date"].widget.attrs.update({
            "min": min_date.isoformat(),
            "max": month_end.isoformat(),
        })

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get("client")
        project = cleaned_data.get("project")
        if client and project and project.client_id != client.id:
            self.add_error("project", "Selected project does not belong to the selected client.")
        return cleaned_data

    def clean_date(self):
        entry_date = self.cleaned_data["date"]
        today = date.today()
        is_current_month = entry_date.year == today.year and entry_date.month == today.month
        is_open_month = OpenMonth.objects.filter(year=entry_date.year, month=entry_date.month).exists()
        if not is_current_month and not is_open_month:
            raise forms.ValidationError(
                "You can only log time for the current month, unless an admin has enabled that month."
            )

        user = self.user or getattr(self.instance, "user", None)
        if user and Leave.objects.filter(
            user=user, from_date__lte=entry_date, to_date__gte=entry_date
        ).exists():
            raise forms.ValidationError("You are on leave on this date and cannot log timesheet hours.")

        if Holiday.objects.filter(date=entry_date).exists():
            raise forms.ValidationError("This date is a holiday and cannot be logged in the timesheet.")

        return entry_date
