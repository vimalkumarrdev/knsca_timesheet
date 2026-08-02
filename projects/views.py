from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin, ManagerRequiredMixin
from config.excel import export_xlsx

from .forms import ProjectForm
from .models import Project


class ProjectListView(ManagerRequiredMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"


class ProjectExportView(ManagerRequiredMixin, View):
    def get(self, request):
        projects = Project.objects.select_related("created_by", "last_updated_by").order_by("name")
        rows = [
            (
                p.name,
                p.created_by.username if p.created_by else "",
                p.last_updated_by.username if p.last_updated_by else "",
                p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "",
            )
            for p in projects
        ]
        return export_xlsx(
            "projects.xlsx",
            ["Name", "Created By", "Last Updated By", "Last Updated At"],
            rows,
        )


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
