from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin, ManagerRequiredMixin
from config.excel import export_xlsx

from .forms import ClientForm, ProjectBulkFormSet, ProjectForm, ProjectInlineFormSet
from .models import Client, Project


class ProjectListView(ManagerRequiredMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return Project.objects.select_related("client", "last_updated_by").order_by("name")


class ProjectExportView(ManagerRequiredMixin, View):
    def get(self, request):
        projects = Project.objects.select_related("client", "created_by", "last_updated_by").order_by("name")
        rows = [
            (
                p.name,
                p.client.name if p.client else "",
                p.get_status_display(),
                p.created_by.username if p.created_by else "",
                p.last_updated_by.username if p.last_updated_by else "",
                p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "",
            )
            for p in projects
        ]
        return export_xlsx(
            "projects.xlsx",
            ["Name", "Client", "Status", "Created By", "Last Updated By", "Last Updated At"],
            rows,
        )


class ProjectBulkCompleteView(AdminRequiredMixin, View):
    def post(self, request):
        project_ids = request.POST.getlist("project_ids")
        Project.objects.filter(pk__in=project_ids).update(
            status=Project.Status.COMPLETED,
            last_updated_by=request.user,
            updated_at=timezone.now(),
        )
        return redirect("projects:list")


class ProjectCreateView(AdminRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    success_url = reverse_lazy("projects:list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.last_updated_by = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(AdminRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    success_url = reverse_lazy("projects:list")

    def form_valid(self, form):
        form.instance.last_updated_by = self.request.user
        return super().form_valid(form)


class ProjectBulkEditView(AdminRequiredMixin, View):
    template_name = "projects/project_bulk_edit.html"

    def get_queryset(self):
        return Project.objects.select_related("client").order_by("name")

    def get(self, request):
        formset = ProjectBulkFormSet(queryset=self.get_queryset(), prefix="projects")
        return render(request, self.template_name, {"formset": formset})

    def post(self, request):
        formset = ProjectBulkFormSet(request.POST, queryset=self.get_queryset(), prefix="projects")
        if formset.is_valid():
            projects = formset.save(commit=False)
            for project in projects:
                project.last_updated_by = request.user
                project.save()
            return redirect("projects:list")
        return render(request, self.template_name, {"formset": formset})


class ClientListView(ManagerRequiredMixin, ListView):
    model = Client
    template_name = "projects/client_list.html"
    context_object_name = "clients"


class ClientCreateView(AdminRequiredMixin, View):
    template_name = "projects/client_form.html"

    def get(self, request):
        client = Client()
        form = ClientForm(instance=client)
        project_formset = ProjectInlineFormSet(instance=client, prefix="projects")
        return render(request, self.template_name, {"form": form, "project_formset": project_formset})

    def post(self, request):
        client = Client()
        form = ClientForm(request.POST, instance=client)
        project_formset = ProjectInlineFormSet(request.POST, instance=client, prefix="projects")
        if form.is_valid() and project_formset.is_valid():
            with transaction.atomic():
                client = form.save(commit=False)
                client.created_by = request.user
                client.last_updated_by = request.user
                client.save()
                project_formset.instance = client
                projects = project_formset.save(commit=False)
                for project in projects:
                    project.created_by = request.user
                    project.last_updated_by = request.user
                    project.save()
                for obj in project_formset.deleted_objects:
                    obj.delete()
            return redirect("projects:client_list")
        return render(request, self.template_name, {"form": form, "project_formset": project_formset})


class ClientUpdateView(AdminRequiredMixin, View):
    template_name = "projects/client_form.html"

    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(instance=client)
        project_formset = ProjectInlineFormSet(instance=client, prefix="projects")
        return render(request, self.template_name, {"form": form, "project_formset": project_formset, "object": client})

    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(request.POST, instance=client)
        project_formset = ProjectInlineFormSet(request.POST, instance=client, prefix="projects")
        if form.is_valid() and project_formset.is_valid():
            with transaction.atomic():
                client = form.save(commit=False)
                client.last_updated_by = request.user
                client.save()
                projects = project_formset.save(commit=False)
                for project in projects:
                    if not project.created_by_id:
                        project.created_by = request.user
                    project.last_updated_by = request.user
                    project.save()
                skipped = []
                for obj in project_formset.deleted_objects:
                    if obj.timesheet_entries.exists():
                        skipped.append(obj.name)
                    else:
                        obj.delete()
            if skipped:
                messages.warning(
                    request,
                    "Could not remove the following projects because they already have logged time: "
                    + ", ".join(skipped),
                )
            return redirect("projects:client_list")
        return render(request, self.template_name, {"form": form, "project_formset": project_formset, "object": client})
