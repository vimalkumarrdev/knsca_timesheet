import datetime
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from accounts.mixins import AdminRequiredMixin, ManagerRequiredMixin
from accounts.models import User
from config.excel import export_xlsx
from projects.models import Project

from .forms import ClaimForm, ClaimTypeForm
from .models import Claim, ClaimType


def _parse_month(get_params):
    today = datetime.date.today()
    try:
        year, month = (int(part) for part in get_params.get("month", "").split("-"))
        return year, month
    except ValueError:
        return today.year, today.month


class MyClaimsView(LoginRequiredMixin, CreateView):
    model = Claim
    form_class = ClaimForm
    template_name = "claims/my_claims.html"
    success_url = reverse_lazy("claims:my_claims")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, "Your claim has been applied successfully.", extra_tags="claim_popup",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["claims"] = Claim.objects.filter(user=self.request.user).select_related(
            "project", "claim_type"
        )
        return context


def _claim_summary(claims):
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


class ClaimReviewView(ManagerRequiredMixin, TemplateView):
    template_name = "claims/review.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = _parse_month(self.request.GET)

        claims = list(
            Claim.objects.filter(from_date__year=year, from_date__month=month)
            .select_related("user", "claim_type", "project", "reviewed_by")
            .order_by("user__username", "-created_at")
        )

        employee_rows = [
            {"user": user_claims[0].user, "total_claims": len(user_claims), "claims": user_claims}
            for _, group in groupby(claims, key=lambda c: c.user_id)
            for user_claims in [list(group)]
        ]

        context["claims"] = claims
        context["employee_rows"] = employee_rows
        context["claim_summary"] = _claim_summary(claims)
        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        return context


class ClaimExportView(ManagerRequiredMixin, View):
    def get(self, request):
        year, month = _parse_month(request.GET)
        claims = Claim.objects.filter(
            from_date__year=year, from_date__month=month
        ).select_related("user", "claim_type", "project").order_by("user__username", "-created_at")
        rows = [
            (
                claim.user.username,
                claim.project.name if claim.project else "",
                claim.claim_type.name,
                claim.from_date,
                claim.to_date,
                float(claim.amount),
                claim.remarks,
                claim.get_status_display(),
                claim.get_settlement_status_display(),
            )
            for claim in claims
        ]
        return export_xlsx(
            f"claims_{year:04d}-{month:02d}.xlsx",
            ["Employee", "Project", "Claim Type", "From", "To", "Amount", "Remarks", "Status", "Settlement"],
            rows,
        )


class ClaimReviewEmployeeExportView(ManagerRequiredMixin, View):
    def get(self, request, user_id):
        year, month = _parse_month(request.GET)
        claims = Claim.objects.filter(
            user_id=user_id, from_date__year=year, from_date__month=month
        ).select_related("user", "claim_type", "project").order_by("-created_at")
        rows = [
            (
                claim.project.name if claim.project else "",
                claim.claim_type.name,
                claim.from_date,
                claim.to_date,
                float(claim.amount),
                claim.remarks,
                claim.get_status_display(),
                claim.get_settlement_status_display(),
            )
            for claim in claims
        ]
        username = claims[0].user.username if claims else User.objects.filter(pk=user_id).values_list("username", flat=True).first()
        return export_xlsx(
            f"claims_{username}_{year:04d}-{month:02d}.xlsx",
            ["Project", "Claim Type", "From", "To", "Amount", "Remarks", "Status", "Settlement"],
            rows,
        )


class ClaimReviewActionView(ManagerRequiredMixin, View):
    def post(self, request, pk, action):
        selected_month = request.POST.get("month", "")
        redirect_url = f"{reverse('claims:review')}?month={selected_month}"

        if action not in ("approve", "reject"):
            return redirect(redirect_url)

        claim = Claim.objects.filter(pk=pk).first()
        if claim:
            claim.status = Claim.Status.APPROVED if action == "approve" else Claim.Status.REJECTED
            claim.reviewed_by = request.user
            claim.reviewed_at = timezone.now()
            claim.save()
        return redirect(redirect_url)


class ClaimReviewBulkApproveView(ManagerRequiredMixin, View):
    def post(self, request):
        selected_month = request.POST.get("month", "")
        claim_ids = request.POST.getlist("claim_ids")
        Claim.objects.filter(pk__in=claim_ids, status=Claim.Status.PENDING).update(
            status=Claim.Status.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        return redirect(f"{reverse('claims:review')}?month={selected_month}")


class ClaimSettlementView(ManagerRequiredMixin, TemplateView):
    template_name = "claims/settlement.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        claims = list(
            Claim.objects.select_related(
                "user", "claim_type", "project", "reviewed_by", "settled_by"
            ).order_by("-created_at")
        )
        context["claims"] = claims
        context["claim_summary"] = _claim_summary(claims)
        return context


class ClaimSettleActionView(ManagerRequiredMixin, View):
    def post(self, request, pk, action):
        if action not in ("settle", "unsettle"):
            return redirect("claims:settlement")

        claim = Claim.objects.filter(pk=pk, status=Claim.Status.APPROVED).first()
        if claim:
            if action == "settle":
                claim.settlement_status = Claim.SettlementStatus.SETTLED
                claim.settled_by = request.user
                claim.settled_at = timezone.now()
            else:
                claim.settlement_status = Claim.SettlementStatus.NOT_SETTLED
                claim.settled_by = None
                claim.settled_at = None
            claim.save()
        return redirect("claims:settlement")


class ClaimSettlementBulkSettleView(ManagerRequiredMixin, View):
    def post(self, request):
        claim_ids = request.POST.getlist("claim_ids")
        Claim.objects.filter(pk__in=claim_ids, status=Claim.Status.APPROVED).update(
            settlement_status=Claim.SettlementStatus.SETTLED,
            settled_by=request.user,
            settled_at=timezone.now(),
        )
        return redirect("claims:settlement")


class ClaimSettlementExportView(ManagerRequiredMixin, View):
    def get(self, request):
        claims = Claim.objects.select_related(
            "user", "claim_type", "project", "settled_by"
        ).order_by("-created_at")
        rows = [
            (
                idx,
                claim.user.username,
                claim.project.name if claim.project else "",
                claim.claim_type.name,
                float(claim.amount),
                claim.get_status_display(),
                claim.get_settlement_status_display(),
                claim.settled_by.username if claim.settled_by else "",
                claim.settled_at.strftime("%B %Y") if claim.settled_at else "",
            )
            for idx, claim in enumerate(claims, start=1)
        ]
        return export_xlsx(
            "claim_settlement.xlsx",
            ["S.No", "Employee", "Project", "Claim Type", "Amount", "Status", "Settlement", "Settled By", "Settled Month"],
            rows,
        )


class ProjectWiseClaimsView(ManagerRequiredMixin, TemplateView):
    template_name = "claims/project_wise.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = _parse_month(self.request.GET)

        claims = list(
            Claim.objects.filter(from_date__year=year, from_date__month=month)
            .select_related("user", "claim_type", "project")
            .order_by("project__name", "-created_at")
        )

        claims_by_project = {}
        unassigned = []
        for claim in claims:
            if claim.project_id:
                claims_by_project.setdefault(claim.project_id, []).append(claim)
            else:
                unassigned.append(claim)

        def _settlement_totals(project_claims):
            pending_approval_amount = sum(
                (c.amount for c in project_claims if c.status == Claim.Status.PENDING),
                start=0,
            )
            settled_amount = sum(
                (c.amount for c in project_claims
                 if c.status == Claim.Status.APPROVED and c.settlement_status == Claim.SettlementStatus.SETTLED),
                start=0,
            )
            not_settled_amount = sum(
                (c.amount for c in project_claims
                 if c.status == Claim.Status.APPROVED and c.settlement_status == Claim.SettlementStatus.NOT_SETTLED),
                start=0,
            )
            return pending_approval_amount, settled_amount, not_settled_amount

        rows = []
        for project in Project.objects.order_by("name"):
            project_claims = claims_by_project.get(project.id, [])
            if not project_claims:
                continue
            pending_approval_amount, settled_amount, not_settled_amount = _settlement_totals(project_claims)
            rows.append({
                "project": project,
                "claims": project_claims,
                "total_claims": len(project_claims),
                "total_amount": sum((c.amount for c in project_claims), start=0),
                "pending_approval_amount": pending_approval_amount,
                "settled_amount": settled_amount,
                "not_settled_amount": not_settled_amount,
            })

        if unassigned:
            pending_approval_amount, settled_amount, not_settled_amount = _settlement_totals(unassigned)
            rows.append({
                "project": None,
                "claims": unassigned,
                "total_claims": len(unassigned),
                "total_amount": sum((c.amount for c in unassigned), start=0),
                "pending_approval_amount": pending_approval_amount,
                "settled_amount": settled_amount,
                "not_settled_amount": not_settled_amount,
            })

        context["rows"] = rows
        context["selected_month"] = f"{year:04d}-{month:02d}"
        context["month_label"] = datetime.date(year, month, 1).strftime("%B %Y")
        return context


class ProjectWiseClaimsExportView(ManagerRequiredMixin, View):
    def get(self, request):
        year, month = _parse_month(request.GET)
        claims = Claim.objects.filter(
            from_date__year=year, from_date__month=month
        ).select_related("user", "claim_type", "project").order_by("project__name", "-created_at")
        rows = [
            (
                claim.project.name if claim.project else "Unassigned",
                claim.user.username,
                claim.claim_type.name,
                claim.from_date,
                claim.to_date,
                float(claim.amount),
                claim.get_status_display(),
                claim.get_settlement_status_display(),
            )
            for claim in claims
        ]
        return export_xlsx(
            f"project_wise_claims_{year:04d}-{month:02d}.xlsx",
            ["Project", "Employee", "Claim Type", "From", "To", "Amount", "Status", "Settlement"],
            rows,
        )


class ClaimTypeListView(AdminRequiredMixin, ListView):
    model = ClaimType
    template_name = "claims/claim_type_list.html"
    context_object_name = "claim_types"


class ClaimTypeCreateView(AdminRequiredMixin, CreateView):
    model = ClaimType
    form_class = ClaimTypeForm
    template_name = "claims/claim_type_form.html"
    success_url = reverse_lazy("claims:claim_type_list")


class ClaimTypeUpdateView(AdminRequiredMixin, UpdateView):
    model = ClaimType
    form_class = ClaimTypeForm
    template_name = "claims/claim_type_form.html"
    success_url = reverse_lazy("claims:claim_type_list")


class ClaimTypeToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        claim_type = ClaimType.objects.filter(pk=pk).first()
        if claim_type:
            claim_type.is_active = not claim_type.is_active
            claim_type.save()
        return redirect("claims:claim_type_list")
