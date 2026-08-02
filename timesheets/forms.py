import calendar
from datetime import date

from django import forms

from .models import TimesheetEntry


class TimesheetEntryForm(forms.ModelForm):
    class Meta:
        model = TimesheetEntry
        fields = ["date", "project", "hours"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0", "max": "24"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].empty_label = "Select Project"
        today = date.today()
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        self.fields["date"].widget.attrs.update({
            "min": month_start.isoformat(),
            "max": month_end.isoformat(),
        })

    def clean_date(self):
        entry_date = self.cleaned_data["date"]
        today = date.today()
        if entry_date.year != today.year or entry_date.month != today.month:
            raise forms.ValidationError("You can only log time for the current month.")
        return entry_date
