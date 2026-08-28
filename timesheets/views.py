import calendar
import datetime
from itertools import groupby

from django.contrib import messages
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
from holidays.models import Holiday
from leaves.models import Leave
from projects.models import Project

from .emails import send_timesheet_reminder, send_timesheet_reminders
from .forms import TimesheetEntryForm
from .models import OpenMonth, TimesheetEntry


def _unavailable_dates_context(user):
    leave_ranges = [
        {"from": leave.from_date.isoformat(), "to": leave.to_date.isoformat()}
        for leave in Leave.objects.filter(user=user)
    ]
    holiday_dates = [
        holiday.date.isoformat() for holiday in Holiday.objects.all()
    ]
    return {"leave_ranges": leave_ranges, "holiday_dates": holiday_dates}


def _project_client_map():
    return {
        str(project.id): project.client_id
        for project in Project.objects.filter(client__isnull=False)
    }


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
    projects = Project.objects.select_related("client").annotate(
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, "Your timesheet entry has been logged successfully.", extra_tags="timesheet_popup",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        entries = TimesheetEntry.objects.filter(
            user=self.request.user, date__year=today.year, date__month=today.month
        ).select_related("project__client")
        context["date_groups"] = _group_entries_by_date(entries)
        context["month_label"] = today.strftime("%B")
        context.update(_unavailable_dates_context(self.request.user))
        context["project_client_map"] = _project_client_map()
        return context


class ViewEntriesView(LoginRequiredMixin, TemplateView):
    template_name = "timesheets/view_entries.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entries = TimesheetEntry.objects.filter(
            user=self.request.user
        ).select_related("project__client")

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_queryset(self):
        return TimesheetEntry.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_unavailable_dates_context(self.request.user))
        context["project_client_map"] = _project_client_map()
        return context


class DeleteDayEntriesView(LoginRequiredMixin, View):
    def get(self, request, date):
        entries = TimesheetEntry.objects.filter(
            user=request.user, date=date
        ).select_related("project__client")
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
        ).select_related("project__client").order_by("user_id", "-date")

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


class ApprovalsEmployeeExportView(ManagerRequiredMixin, View):
    def get(self, request, user_id):
        year, month = _parse_month(request.GET)
        entries = TimesheetEntry.objects.filter(
            user_id=user_id, date__year=year, date__month=month
        ).select_related("user", "project__client").order_by("-date")

        rows = [
            (
                entry.date,
                entry.project.client.name if entry.project.client else "",
                entry.project.name,
                float(entry.hours),
                entry.get_work_mode_display(),
                entry.remarks,
            )
            for entry in entries
        ]
        username = entries[0].user.username if entries else User.objects.filter(pk=user_id).values_list("username", flat=True).first()
        return export_xlsx(
            f"timesheet_{username}_{year:04d}-{month:02d}.xlsx",
            ["Date", "Client", "Project", "Hours", "Work Mode", "Remarks"],
            rows,
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

        headers = ["Client", "Project"] + day_labels + [f"Total ({month_label})"]
        data_rows = [
            (row["project"].client.name if row["project"].client else "", row["project"].name)
            + tuple(float(h) if h is not None else "" for h in row["daily_hours"])
            + (float(row["total_hours"]),)
            for row in rows
        ]
        return export_xlsx(
            f"project_timesheet_{year:04d}-{month:02d}.xlsx",
            headers,
            data_rows,
        )


class ProjectTimesheetProjectExportView(ManagerRequiredMixin, View):
    def get(self, request, project_id):
        year, month = _parse_month(request.GET)
        entries = TimesheetEntry.objects.filter(
            project_id=project_id, date__year=year, date__month=month
        ).select_related("user", "project__client").order_by("-date")

        rows = [
            (entry.user.username, entry.date, float(entry.hours))
            for entry in entries
        ]
        project = Project.objects.select_related("client").filter(pk=project_id).first()
        project_name = project.name if project else ""
        return export_xlsx(
            f"project_timesheet_{project_name}_{year:04d}-{month:02d}.xlsx",
            ["Employee", "Date", "Hours"],
            rows,
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


class SendTimesheetRemindersView(ManagerRequiredMixin, View):
    def post(self, request):
        selected_month = request.POST.get("month", "")
        try:
            year, month = (int(part) for part in selected_month.split("-"))
        except ValueError:
            today = datetime.date.today()
            year, month = today.year, today.month

        reminded = send_timesheet_reminders(year, month)
        if reminded:
            messages.success(request, f"Sent {len(reminded)} reminder email(s).")
        else:
            messages.info(request, "No reminders needed — everyone is up to date.")

        redirect_url = request.POST.get("next") or "dashboard:home"
        return redirect(redirect_url)


class SendTimesheetReminderView(ManagerRequiredMixin, View):
    def post(self, request, user_id):
        selected_month = request.POST.get("month", "")
        try:
            year, month = (int(part) for part in selected_month.split("-"))
        except ValueError:
            today = datetime.date.today()
            year, month = today.year, today.month

        employee = User.objects.filter(pk=user_id, role=User.Role.EMPLOYEE).first()
        if not employee:
            messages.error(request, "That employee could not be found.")
        elif send_timesheet_reminder(employee, year, month):
            messages.success(request, f"Reminder email sent to {employee.username}.")
        else:
            messages.info(request, f"{employee.username} has no unfilled days (or no email on file) — nothing sent.")

        redirect_url = request.POST.get("next") or "dashboard:home"
        return redirect(redirect_url)


class SendSelectedTimesheetRemindersView(ManagerRequiredMixin, View):
    def post(self, request):
        selected_month = request.POST.get("month", "")
        try:
            year, month = (int(part) for part in selected_month.split("-"))
        except ValueError:
            today = datetime.date.today()
            year, month = today.year, today.month

        user_ids = request.POST.getlist("user_ids")
        employees = User.objects.filter(pk__in=user_ids, role=User.Role.EMPLOYEE)
        reminded = [e.username for e in employees if send_timesheet_reminder(e, year, month)]

        if reminded:
            messages.success(request, f"Sent {len(reminded)} reminder email(s): {', '.join(reminded)}")
        else:
            messages.info(request, "No reminders were sent — the selected employees may already be up to date.")

        redirect_url = request.POST.get("next") or "dashboard:home"
        return redirect(redirect_url)
