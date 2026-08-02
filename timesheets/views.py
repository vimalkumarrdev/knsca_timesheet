import datetime
from itertools import groupby

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from accounts.mixins import ManagerRequiredMixin
from accounts.models import User
from config.excel import export_xlsx

from .forms import TimesheetEntryForm
from .models import TimesheetEntry


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

        users = _employee_month_totals(year, month)

        entries = TimesheetEntry.objects.filter(
            date__year=year, date__month=month
        ).select_related("project").order_by("user_id", "-date")

        entries_by_user = {
            user_id: _group_entries_by_date(list(group))
            for user_id, group in groupby(entries, key=lambda e: e.user_id)
        }

        context["rows"] = [
            {"user": u, "total_hours": u.total_hours, "date_groups": entries_by_user.get(u.id, [])}
            for u in users
        ]
        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        return context


class ApprovalsExportView(ManagerRequiredMixin, View):
    def get(self, request):
        year, month = _parse_month(request.GET)
        users = _employee_month_totals(year, month)
        month_label = datetime.date(year, month, 1).strftime("%B %Y")
        rows = [(u.username, float(u.total_hours)) for u in users]
        return export_xlsx(
            f"timesheets_{year:04d}-{month:02d}.xlsx",
            ["Employee", f"Total hours ({month_label})"],
            rows,
        )
