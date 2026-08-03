from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView


@login_required
def redirect_by_role(request):
    role = request.user.role
    if role == "ADMIN":
        return redirect("dashboard:home")
    if role == "MANAGER":
        return redirect("dashboard:home")
    return redirect("timesheets:my_week")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class AccountPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"
