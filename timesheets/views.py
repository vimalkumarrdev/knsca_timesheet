import calendar
import datetime
from itertools import groupby

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from accounts.mixins import AdminRequiredMixin, ManagerRequiredMixin
from accounts.models import User
from config.excel import export_xlsx
from projects.models import Project

from .forms import TimesheetEntryForm
from .models import OpenMonth, TimesheetEntry


def _group_entries_by_date(entries):
    return [
        {"date": entry_date, "entries": day_entries, "total_hours": sum(e.hours for e in day_entries)}
        for entry_date, group in groupby(entries, key=lambda e: e.date)
        for day_entries in [list(group)]
    ]


def _parse_month(get_params):
    today = datetime.date.today()
    try:
        year, month = (int(part) for part in get_params.get("month", "").split("-"))
        return year, month
    except ValueError:
        return today.year, today.month


def _employee_month_totals(year, month):
    return User.objects.filter(role=User.Role.EMPLOYEE).annotate(
        total_hours=Coalesce(
            Sum(
                "timesheet_entries__hours",
                filter=Q(timesheet_entries__date__year=year, timesheet_entries__date__month=month),
            ),
            0,
            output_field=DecimalField(max_digits=6, decimal_places=2),
        )
    ).order_by("username")


def _build_day_cells(date_groups, day_range):
    groups_by_day = {g["date"].day: g for g in date_groups}
    return [{"day": d, "group": groups_by_day.get(d)} for d in day_range]


def _month_day_labels(year, month):
    num_days = calendar.monthrange(year, month)[1]
    day_range = list(range(1, num_days + 1))
    month_abbr = datetime.date(year, month, 1).strftime("%b")
    day_labels = [f"{month_abbr}{d}" for d in day_range]
    return day_range, day_labels


def _employee_daily_grid(year, month):
    users = _employee_month_totals(year, month)

    num_days = calendar.monthrange(year, month)[1]
    day_range = list(range(1, num_days + 1))

    daily_totals = (
        TimesheetEntry.objects.filter(
            user__role=User.Role.EMPLOYEE, date__year=year, date__month=month
        )
        .values("user_id", "date")
        .annotate(day_hours=Sum("hours"))
    )
    hours_by_user_day = {}
    for row in daily_totals:
        hours_by_user_day.setdefault(row["user_id"], {})[row["date"].day] = row["day_hours"]

    rows = [
        {
            "user": u,
            "total_hours": u.total_hours,
            "daily_hours": [hours_by_user_day.get(u.id, {}).get(d) for d in day_range],
        }
        for u in users
    ]
    return day_range, rows


def _project_daily_grid(year, month):
    projects = Project.objects.annotate(
        total_hours=Coalesce(
            Sum(
                "timesheet_entries__hours",
                filter=Q(timesheet_entries__date__year=year, timesheet_entries__date__month=month),
            ),
            0,
            output_field=DecimalField(max_digits=8, decimal_places=2),
        )
    ).order_by("name")

    day_range, _ = _month_day_labels(year, month)

    daily_totals = (
        TimesheetEntry.objects.filter(date__year=year, date__month=month)
        .values("project_id", "date")
        .annotate(day_hours=Sum("hours"))
    )
    hours_by_project_day = {}
    for row in daily_totals:
        hours_by_project_day.setdefault(row["project_id"], {})[row["date"].day] = row["day_hours"]

    rows = [
        {
            "project": p,
            "total_hours": p.total_hours,
            "daily_hours": [hours_by_project_day.get(p.id, {}).get(d) for d in day_range],
        }
        for p in projects
    ]
    return day_range, rows


class MyWeekView(LoginRequiredMixin, CreateView):
    model = TimesheetEntry
    form_class = TimesheetEntryForm
    template_name = "timesheets/my_week.html"
    success_url = reverse_lazy("timesheets:my_week")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        entries = TimesheetEntry.objects.filter(
            user=self.request.user, date__year=today.year, date__month=today.month
        ).select_related("project")
        context["date_groups"] = _group_entries_by_date(entries)
        context["month_label"] = today.strftime("%B")
        return context


class ViewEntriesView(LoginRequiredMixin, TemplateView):
    template_name = "timesheets/view_entries.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entries = TimesheetEntry.objects.filter(
            user=self.request.user
        ).select_related("project")

        selected_month = self.request.GET.get("month", "")
        if selected_month:
            try:
                year, month = (int(part) for part in selected_month.split("-"))
                entries = entries.filter(date__year=year, date__month=month)
            except ValueError:
                selected_month = ""

        month_groups = []
        for (year, month), month_entries in groupby(
            entries, key=lambda e: (e.date.year, e.date.month)
        ):
            month_entries = list(month_entries)
            month_groups.append({
                "label": datetime.date(year, month, 1).strftime("%B %Y"),
                "total_hours": sum(e.hours for e in month_entries),
                "date_groups": _group_entries_by_date(month_entries),
            })
        context["month_groups"] = month_groups
        context["selected_month"] = selected_month
        return context


class TimesheetEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = TimesheetEntry
    form_class = TimesheetEntryForm
    template_name = "timesheets/entry_form.html"
    success_url = reverse_lazy("timesheets:my_week")

    def get_queryset(self):
        return TimesheetEntry.objects.filter(user=self.request.user)


class DeleteDayEntriesView(LoginRequiredMixin, View):
    def get(self, request, date):
        entries = TimesheetEntry.objects.filter(
            user=request.user, date=date
        ).select_related("project")
        if not entries.exists():
            return redirect("timesheets:my_week")
        return render(
            request,
            "timesheets/confirm_delete_day.html",
            {"date": date, "entries": entries},
        )

    def post(self, request, date):
        TimesheetEntry.objects.filter(user=request.user, date=date).delete()
        return redirect("timesheets:my_week")


class ApprovalsView(ManagerRequiredMixin, TemplateView):
    template_name = "timesheets/approvals.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = _parse_month(self.request.GET)

        day_range, rows = _employee_daily_grid(year, month)

        entries = TimesheetEntry.objects.filter(
            date__year=year, date__month=month
        ).select_related("project").order_by("user_id", "-date")

        entries_by_user = {
            user_id: _group_entries_by_date(list(group))
            for user_id, group in groupby(entries, key=lambda e: e.user_id)
        }

        for row in rows:
            date_groups = entries_by_user.get(row["user"].id, [])
            row["date_groups"] = date_groups
            row["day_cells"] = _build_day_cells(date_groups, day_range)

        _, day_labels = _month_day_labels(year, month)

        context["rows"] = rows
        context["day_range"] = day_range
        context["day_labels"] = day_labels
        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        return context


class ApprovalsExportView(ManagerRequiredMixin, View):
    def get(self, request):
        year, month = _parse_month(request.GET)
        _, rows = _employee_daily_grid(year, month)
        month_label = datetime.date(year, month, 1).strftime("%B %Y")
        _, day_labels = _month_day_labels(year, month)

        headers = ["Employee"] + day_labels + [f"Total ({month_label})"]
        data_rows = [
            (row["user"].username,)
            + tuple(float(h) if h is not None else "" for h in row["daily_hours"])
            + (float(row["total_hours"]),)
            for row in rows
        ]
        return export_xlsx(
            f"timesheets_{year:04d}-{month:02d}.xlsx",
            headers,
            data_rows,
        )


class ProjectTimesheetView(ManagerRequiredMixin, TemplateView):
    template_name = "timesheets/project_timesheet.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = _parse_month(self.request.GET)

        projects = Project.objects.annotate(
            total_hours=Coalesce(
                Sum(
                    "timesheet_entries__hours",
                    filter=Q(timesheet_entries__date__year=year, timesheet_entries__date__month=month),
                ),
                0,
                output_field=DecimalField(max_digits=8, decimal_places=2),
            )
        ).order_by("name")

        entries = TimesheetEntry.objects.filter(
            date__year=year, date__month=month
        ).select_related("user").order_by("project_id", "-date")
        entries_by_project = {
            project_id: list(group)
            for project_id, group in groupby(entries, key=lambda e: e.project_id)
        }

        day_range, day_labels = _month_day_labels(year, month)

        rows = []
        for p in projects:
            flat_entries = entries_by_project.get(p.id, [])
            date_groups = _group_entries_by_date(flat_entries)
            rows.append({
                "project": p,
                "total_hours": p.total_hours,
                "entries": flat_entries,
                "day_cells": _build_day_cells(date_groups, day_range),
            })

        context["rows"] = rows
        context["day_range"] = day_range
        context["day_labels"] = day_labels
        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        return context


class ProjectTimesheetExportView(ManagerRequiredMixin, View):
    def get(self, request):
        year, month = _parse_month(request.GET)
        _, rows = _project_daily_grid(year, month)
        month_label = datetime.date(year, month, 1).strftime("%B %Y")
        _, day_labels = _month_day_labels(year, month)

        headers = ["Project"] + day_labels + [f"Total ({month_label})"]
        data_rows = [
            (row["project"].name,)
            + tuple(float(h) if h is not None else "" for h in row["daily_hours"])
            + (float(row["total_hours"]),)
            for row in rows
        ]
        return export_xlsx(
            f"project_timesheet_{year:04d}-{month:02d}.xlsx",
            headers,
            data_rows,
        )


class OpenMonthView(AdminRequiredMixin, TemplateView):
    template_name = "timesheets/open_months.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["open_months"] = [
            {"obj": om, "label": datetime.date(om.year, om.month, 1).strftime("%B %Y")}
            for om in OpenMonth.objects.select_related("enabled_by")
        ]
        return context

    def post(self, request, *args, **kwargs):
        try:
            year, month = (int(part) for part in request.POST.get("month", "").split("-"))
        except ValueError:
            return redirect("timesheets:open_months")

        OpenMonth.objects.get_or_create(
            year=year, month=month, defaults={"enabled_by": request.user}
        )
        return redirect("timesheets:open_months")


class OpenMonthDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        OpenMonth.objects.filter(pk=pk).delete()
        return redirect("timesheets:open_months")
