from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView

from accounts.mixins import ManagerRequiredMixin

from .forms import LeaveForm
from .models import Leave


class ManageLeavesView(ManagerRequiredMixin, CreateView):
    model = Leave
    form_class = LeaveForm
    template_name = "leaves/manage_leaves.html"
    success_url = reverse_lazy("leaves:manage")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["leaves"] = Leave.objects.select_related("user", "created_by").order_by("-from_date")
        return context


class LeaveDeleteView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        Leave.objects.filter(pk=pk).delete()
        return redirect("leaves:manage")
