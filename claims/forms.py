from django import forms

from projects.models import Client, Project

from .models import Claim, ClaimType


class ClaimForm(forms.ModelForm):
    client = forms.ModelChoiceField(queryset=Client.objects.order_by("name"), required=True, label="Client")

    class Meta:
        model = Claim
        fields = ["client", "project", "claim_type", "date", "amount", "bill_copy", "remarks"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={
                "step": "1",
                "min": "0",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
                "onkeydown": "return event.key !== '.' && event.key !== ',' && event.key !== 'e' && event.key !== 'E';",
                "oninput": "if (/[.,]/.test(this.value)) { this.value = this.value.split(/[.,]/)[0]; }",
            }),
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
