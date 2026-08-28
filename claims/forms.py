from django import forms

from projects.models import Client, Project

from .models import Claim, ClaimType


class ClaimForm(forms.ModelForm):
    client = forms.ModelChoiceField(queryset=Client.objects.order_by("name"), required=True, label="Client")

    class Meta:
        model = Claim
        fields = ["client", "project", "claim_type", "from_date", "to_date", "amount", "bill_copy", "remarks"]
        widgets = {
            "from_date": forms.DateInput(attrs={"type": "date"}),
            "to_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Optional notes…"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].empty_label = "Select client"
        self.fields["project"].queryset = Project.objects.select_related("client").filter(
            client__isnull=False
        ).order_by("name")
        self.fields["project"].empty_label = "Select project"
        self.fields["claim_type"].queryset = ClaimType.objects.filter(is_active=True)
        self.fields["claim_type"].empty_label = "Select claim type"
        self.fields["bill_copy"].required = False

        if self.instance and self.instance.pk and self.instance.project_id:
            self.fields["client"].initial = self.instance.project.client_id

    def clean(self):
        cleaned_data = super().clean()
        claim_type = cleaned_data.get("claim_type")
        bill_copy = cleaned_data.get("bill_copy")
        if claim_type and claim_type.bill_required and not bill_copy:
            self.add_error("bill_copy", "A bill copy is required for this claim type.")

        from_date = cleaned_data.get("from_date")
        to_date = cleaned_data.get("to_date")
        if from_date and to_date and to_date < from_date:
            raise forms.ValidationError("To date cannot be before from date.")

        client = cleaned_data.get("client")
        project = cleaned_data.get("project")
        if client and project and project.client_id != client.id:
            self.add_error("project", "Selected project does not belong to the selected client.")
        return cleaned_data


class ClaimTypeForm(forms.ModelForm):
    class Meta:
        model = ClaimType
        fields = ["name", "bill_required"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Claim type name"}),
        }
