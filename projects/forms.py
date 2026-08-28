from django import forms
from django.forms import inlineformset_factory, modelformset_factory

from .models import Client, Project


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Client name"}),
            "status": forms.RadioSelect(),
        }


class ProjectForm(forms.ModelForm):
    client = forms.ModelChoiceField(queryset=Client.objects.order_by("name"), required=True, label="Client")

    class Meta:
        model = Project
        fields = ["name", "client", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Project name"}),
            "status": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].empty_label = "Select Client"


ProjectInlineFormSet = inlineformset_factory(
    Client,
    Project,
    fields=["name"],
    extra=3,
    can_delete=True,
    widgets={"name": forms.TextInput(attrs={"placeholder": "Project name"})},
)


class ProjectBulkForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Project name", "style": "width: 400px; max-width: 100%;"}),
        }


ProjectBulkFormSet = modelformset_factory(Project, form=ProjectBulkForm, extra=0)
