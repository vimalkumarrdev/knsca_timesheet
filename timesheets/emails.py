import calendar
import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from accounts.models import User

from .models import TimesheetEntry


def _working_days(year, month):
    total_days = calendar.monthrange(year, month)[1]
    return sum(
        1
        for day in range(1, total_days + 1)
        if datetime.date(year, month, day).weekday() < 5
    )


def _send_reminder(employee, year, month, working_days, filled_days):
    remaining_days = max(working_days - filled_days, 0)
    if remaining_days == 0 or not employee.email:
        return False

    month_label = datetime.date(year, month, 1).strftime("%B %Y")
    timesheet_url = f"{settings.SITE_URL}{reverse('timesheets:my_week')}"
    name = employee.first_name or employee.username
    message = (
        f"Hi {name},\n\n"
        f"You've filled {filled_days} of {working_days} working days on your timesheet for {month_label}. "
        f"{remaining_days} day(s) are still missing.\n\n"
        f"Please log your remaining hours here: {timesheet_url}\n\n"
        f"— KNSCA Timesheet & Claim Portal"
    )
    send_mail(
        subject=f"Reminder: {remaining_days} timesheet day(s) pending for {month_label}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[employee.email],
        fail_silently=False,
    )
    return True


def send_timesheet_reminder(employee, year, month):
    """Email a single employee if they still have unfilled working days this month.

    Returns True if an email was sent, False otherwise.
    """
    working_days = _working_days(year, month)
    filled_days = (
        TimesheetEntry.objects.filter(user=employee, date__year=year, date__month=month)
        .values("date").distinct().count()
    )
    return _send_reminder(employee, year, month, working_days, filled_days)


def send_timesheet_reminders(year, month):
    """Email every employee who still has unfilled working days this month.

    Returns the list of usernames who were emailed.
    """
    working_days = _working_days(year, month)
    entries = TimesheetEntry.objects.filter(date__year=year, date__month=month)

    reminded = []
    for employee in User.objects.filter(role=User.Role.EMPLOYEE, is_active=True).order_by("username"):
        filled_days = entries.filter(user=employee).values("date").distinct().count()
        if _send_reminder(employee, year, month, working_days, filled_days):
            reminded.append(employee.username)

    return reminded
