from django import forms

from .models import Holiday


class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = ["date", "name", "holiday_type"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Diwali, Republic Day…"}),
            "holiday_type": forms.RadioSelect(),
        }
