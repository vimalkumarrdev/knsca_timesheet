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
]
