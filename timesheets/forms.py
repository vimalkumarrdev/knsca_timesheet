import calendar
from datetime import date

from django import forms

from .models import OpenMonth, TimesheetEntry


class TimesheetEntryForm(forms.ModelForm):
    class Meta:
        model = TimesheetEntry
        fields = ["date", "project", "hours", "work_mode", "remarks"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0", "max": "24"}),
            "work_mode": forms.RadioSelect(),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Optional notes…"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].empty_label = "Select Project"
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

    def clean_date(self):
        entry_date = self.cleaned_data["date"]
        today = date.today()
        if entry_date.year == today.year and entry_date.month == today.month:
            return entry_date
        if OpenMonth.objects.filter(year=entry_date.year, month=entry_date.month).exists():
            return entry_date
        raise forms.ValidationError(
            "You can only log time for the current month, unless an admin has enabled that month."
        )
