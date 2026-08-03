from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView

from accounts.mixins import ManagerRequiredMixin

from .forms import HolidayForm
from .models import Holiday


class ManageHolidaysView(ManagerRequiredMixin, CreateView):
    model = Holiday
    form_class = HolidayForm
    template_name = "holidays/manage_holidays.html"
    success_url = reverse_lazy("holidays:manage")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["holidays"] = Holiday.objects.select_related("created_by").order_by("date")
        return context


class HolidayDeleteView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        Holiday.objects.filter(pk=pk).delete()
        return redirect("holidays:manage")
