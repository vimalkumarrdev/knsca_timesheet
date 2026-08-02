from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def redirect_by_role(request):
    role = request.user.role
    if role == "ADMIN":
        return redirect("dashboard:home")
    if role == "MANAGER":
        return redirect("dashboard:home")
    return redirect("timesheets:my_week")
