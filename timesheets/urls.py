from django.urls import path

from . import views

app_name = "timesheets"

urlpatterns = [
    path("my-week/", views.MyWeekView.as_view(), name="my_week"),
    path("view-entries/", views.ViewEntriesView.as_view(), name="view_entries"),
    path("entries/<int:pk>/edit/", views.TimesheetEntryUpdateView.as_view(), name="edit_entry"),
    path("day/<str:date>/delete/", views.DeleteDayEntriesView.as_view(), name="delete_day"),
    path("approvals/", views.ApprovalsView.as_view(), name="approvals"),
    path("approvals/export/", views.ApprovalsExportView.as_view(), name="approvals_export"),
    path("approvals/<int:user_id>/export/", views.ApprovalsEmployeeExportView.as_view(), name="approvals_employee_export"),
    path("project-timesheet/", views.ProjectTimesheetView.as_view(), name="project_timesheet"),
    path("project-timesheet/export/", views.ProjectTimesheetExportView.as_view(), name="project_timesheet_export"),
    path("project-timesheet/<int:project_id>/export/", views.ProjectTimesheetProjectExportView.as_view(), name="project_timesheet_project_export"),
    path("open-months/", views.OpenMonthView.as_view(), name="open_months"),
    path("open-months/<int:pk>/delete/", views.OpenMonthDeleteView.as_view(), name="open_months_delete"),
]
