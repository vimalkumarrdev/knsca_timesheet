from django import forms

from accounts.models import User

from .models import Leave


class LeaveForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE).order_by("username"),
        label="Employee",
    )

    class Meta:
        model = Leave
        fields = ["user", "from_date", "to_date", "reason"]
        widgets = {
            "from_date": forms.DateInput(attrs={"type": "date"}),
            "to_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.TextInput(attrs={"placeholder": "Optional reason…"}),
        }

    def clean(self):
        cleaned = super().clean()
        from_date = cleaned.get("from_date")
        to_date = cleaned.get("to_date")
        if from_date and to_date and to_date < from_date:
            raise forms.ValidationError("To date cannot be before from date.")
        return cleaned
