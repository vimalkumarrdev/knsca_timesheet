from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView

from .forms import AdminUserCreateForm
from .mixins import AdminRequiredMixin
from .models import User


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


class UserManagementListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.order_by("username")


class UserManagementCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = AdminUserCreateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        messages.success(self.request, f"User \"{form.cleaned_data['username']}\" was created successfully.")
        return super().form_valid(form)


class UserManagementToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        target = User.objects.filter(pk=pk).first()
        if not target:
            return redirect("accounts:user_list")

        if target == request.user:
            messages.error(request, "You cannot disable your own account.")
            return redirect("accounts:user_list")

        target.is_active = not target.is_active
        target.save()
        return redirect("accounts:user_list")
