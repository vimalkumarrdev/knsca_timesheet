import calendar
import datetime

from django.db.models import Sum
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import ManagerRequiredMixin
from accounts.models import User
from claims.models import Claim, ClaimType
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


def _claim_type_rows():
    claim_types = ClaimType.objects.order_by("name")
    claims = Claim.objects.select_related("user", "claim_type", "project__client").order_by("claim_type_id", "-created_at")

    claims_by_type = {}
    for claim in claims:
        claims_by_type.setdefault(claim.claim_type_id, []).append(claim)

    status_config = [
        (Claim.Status.PENDING, "Pending", "#f59e0b"),
        (Claim.Status.APPROVED, "Approved", "#16a34a"),
        (Claim.Status.REJECTED, "Rejected", "#dc2626"),
    ]

    rows = []
    for ct in claim_types:
        ct_claims = claims_by_type.get(ct.id, [])
        rows.append({
            "claim_type": ct,
            "claims": ct_claims,
            "counts": [sum(1 for c in ct_claims if c.status == status_value) for status_value, _, _ in status_config],
        })

    status_series = [
        {"status": label, "color": color, "counts": [row["counts"][i] for row in rows]}
        for i, (_, label, color) in enumerate(status_config)
    ]
    return rows, status_series


def _claim_summary(year, month):
    claims = list(
        Claim.objects.filter(date__year=year, date__month=month)
        .select_related("user", "claim_type", "project__client")
    )

    categories = [
        ("overall", "Overall Claims", lambda c: True),
        ("approved", "Approved Claims", lambda c: c.status == Claim.Status.APPROVED),
        ("pending", "Pending Claims", lambda c: c.status == Claim.Status.PENDING),
        ("rejected", "Rejected Claims", lambda c: c.status == Claim.Status.REJECTED),
        (
            "settled", "Settled Claims",
            lambda c: c.status == Claim.Status.APPROVED and c.settlement_status == Claim.SettlementStatus.SETTLED,
        ),
        (
            "unsettled", "Un-settled Claims",
            lambda c: c.status == Claim.Status.APPROVED and c.settlement_status == Claim.SettlementStatus.NOT_SETTLED,
        ),
    ]

    summary = {}
    for key, label, predicate in categories:
        matched = [c for c in claims if predicate(c)]
        summary[key] = {
            "label": label,
            "count": len(matched),
            "total_amount": sum((c.amount for c in matched), start=0),
            "claims": matched,
        }
    return summary


def _project_claim_status_series(year, month):
    claims = list(
        Claim.objects.filter(date__year=year, date__month=month)
        .select_related("project__client", "user", "claim_type")
    )

    claims_by_project = {}
    for claim in claims:
        key = claim.project.name if claim.project else "Unassigned"
        claims_by_project.setdefault(key, []).append(claim)

    project_labels = sorted(claims_by_project.keys())
    project_client_labels = {}
    for label in project_labels:
        project = claims_by_project[label][0].project
        project_client_labels[label] = project.client.name if project and project.client else None

    status_config = [
        ("Pending", "#f59e0b", lambda c: c.status == Claim.Status.PENDING),
        ("Approved", "#2563eb", lambda c: c.status == Claim.Status.APPROVED),
        (
            "Settled", "#16a34a",
            lambda c: c.status == Claim.Status.APPROVED and c.settlement_status == Claim.SettlementStatus.SETTLED,
        ),
        (
            "Not Settled", "#dc2626",
            lambda c: c.status == Claim.Status.APPROVED and c.settlement_status == Claim.SettlementStatus.NOT_SETTLED,
        ),
    ]

    status_series = []
    detail_rows = []
    for status_idx, (label, color, predicate) in enumerate(status_config):
        counts = []
        for project_idx, project_label in enumerate(project_labels):
            matched = [c for c in claims_by_project.get(project_label, []) if predicate(c)]
            counts.append(len(matched))
            if matched:
                detail_rows.append({
                    "project_idx": project_idx,
                    "status_idx": status_idx,
                    "project_label": project_label,
                    "client_label": project_client_labels[project_label],
                    "status_label": label,
                    "claims": matched,
                })
        status_series.append({"status": label, "color": color, "counts": counts})

    return project_labels, status_series, detail_rows


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

        claim_type_rows, claim_status_series = _claim_type_rows()
        project_claim_labels, project_claim_status_series, project_claim_details = _project_claim_status_series(year, month)
        claim_summary = _claim_summary(year, month)

        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        context["working_days"] = working_days
        context["rows"] = rows
        context["project_chart_labels"] = [p["project__name"] for p in project_totals]
        context["project_chart_values"] = [float(p["total_hours"]) for p in project_totals]
        context["employee_chart_labels"] = employee_usernames
        context["employee_project_series"] = employee_project_series
        context["claim_type_rows"] = claim_type_rows
        context["claim_chart_labels"] = [row["claim_type"].name for row in claim_type_rows]
        context["claim_chart_ids"] = [row["claim_type"].id for row in claim_type_rows]
        context["claim_status_series"] = claim_status_series
        context["project_claim_labels"] = project_claim_labels
        context["project_claim_status_series"] = project_claim_status_series
        context["project_claim_details"] = project_claim_details
        context["claim_summary"] = claim_summary
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
