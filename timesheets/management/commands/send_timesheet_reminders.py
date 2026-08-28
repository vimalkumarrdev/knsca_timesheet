import datetime

from django.core.management.base import BaseCommand

from timesheets.emails import send_timesheet_reminders


class Command(BaseCommand):
    help = "Emails employees who still have unfilled timesheet days for the given month (default: current month)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            help="Month to check, formatted YYYY-MM. Defaults to the current month.",
        )

    def handle(self, *args, **options):
        today = datetime.date.today()
        year, month = today.year, today.month
        if options["month"]:
            try:
                year, month = (int(part) for part in options["month"].split("-"))
            except ValueError:
                self.stderr.write(self.style.ERROR("--month must be formatted YYYY-MM"))
                return

        reminded = send_timesheet_reminders(year, month)
        if reminded:
            self.stdout.write(self.style.SUCCESS(f"Sent {len(reminded)} reminder(s): {', '.join(reminded)}"))
        else:
            self.stdout.write("No reminders needed — everyone is up to date.")
