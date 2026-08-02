import calendar
import datetime

from django.db.models import Sum
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import ManagerRequiredMixin
from accounts.models import User
from config.excel import export_xlsx
from projects.models import Project
from timesheets.models import TimesheetEntry


def _parse_month(get_params):
    today = datetime.date.today()
    try:
        year, month = (int(part) for part in get_params.get("month", "").split("-"))
        return year, month
    except ValueError:
        return today.year, today.month


def _working_days(year, month):
    total_days = calendar.monthrange(year, month)[1]
    return sum(
        1
        for day in range(1, total_days + 1)
        if datetime.date(year, month, day).weekday() < 5
    )


def _days_filled_rows(year, month):
    entries = TimesheetEntry.objects.filter(date__year=year, date__month=month)
    working_days = _working_days(year, month)
    rows = []
    for emp in User.objects.filter(role=User.Role.EMPLOYEE).order_by("username"):
        filled_days = entries.filter(user=emp).values("date").distinct().count()
        rows.append({
            "user": emp,
            "filled_days": filled_days,
            "remaining_days": max(working_days - filled_days, 0),
        })
    return working_days, rows


class DashboardHomeView(ManagerRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = _parse_month(self.request.GET)

        entries = TimesheetEntry.objects.filter(date__year=year, date__month=month)

        project_totals = list(
            entries.values("project__name")
            .annotate(total_hours=Sum("hours"))
            .order_by("project__name")
        )
        employee_usernames = list(
            User.objects.filter(role=User.Role.EMPLOYEE).order_by("username").values_list("username", flat=True)
        )

        employee_project_totals = (
            entries.filter(user__role=User.Role.EMPLOYEE)
            .values("user__username", "project__name")
            .annotate(total_hours=Sum("hours"))
        )
        hours_lookup = {
            (row["user__username"], row["project__name"]): float(row["total_hours"])
            for row in employee_project_totals
        }
        project_names = list(Project.objects.order_by("name").values_list("name", flat=True))
        employee_project_series = [
            {
                "project": project_name,
                "hours": [hours_lookup.get((username, project_name), 0) for username in employee_usernames],
            }
            for project_name in project_names
        ]

        working_days, rows = _days_filled_rows(year, month)

        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        context["working_days"] = working_days
        context["rows"] = rows
        context["project_chart_labels"] = [p["project__name"] for p in project_totals]
        context["project_chart_values"] = [float(p["total_hours"]) for p in project_totals]
        context["employee_chart_labels"] = employee_usernames
        context["employee_project_series"] = employee_project_series
        return context


class DashboardExportView(ManagerRequiredMixin, View):
    def get(self, request):
        year, month = _parse_month(request.GET)
        _, rows = _days_filled_rows(year, month)
        month_label = datetime.date(year, month, 1).strftime("%B %Y")
        data_rows = [(r["user"].username, r["filled_days"], r["remaining_days"]) for r in rows]
        return export_xlsx(
            f"dashboard_days_filled_{year:04d}-{month:02d}.xlsx",
            ["Employee", f"Days Filled ({month_label})", "Remaining"],
            data_rows,
        )
