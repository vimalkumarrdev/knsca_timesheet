from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="list"),
    path("export/", views.ProjectExportView.as_view(), name="export"),
    path("add/", views.ProjectCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
]
