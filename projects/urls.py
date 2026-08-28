from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="list"),
    path("export/", views.ProjectExportView.as_view(), name="export"),
    path("add/", views.ProjectCreateView.as_view(), name="add"),
    path("bulk-edit/", views.ProjectBulkEditView.as_view(), name="bulk_edit"),
    path("bulk-complete/", views.ProjectBulkCompleteView.as_view(), name="bulk_complete"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
    path("clients/", views.ClientListView.as_view(), name="client_list"),
    path("clients/add/", views.ClientCreateView.as_view(), name="client_add"),
    path("clients/<int:pk>/edit/", views.ClientUpdateView.as_view(), name="client_edit"),
]
