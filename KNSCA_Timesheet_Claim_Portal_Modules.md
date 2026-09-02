% KNSCA Timesheet & Claim Portal — Modules & Functionalities

# KNSCA Timesheet & Claim Portal
## Modules & Functionalities

---

## 1. Accounts (Authentication & User Management)

- Login/logout, role-based redirect (Employee / Manager / Admin)
- User profile view and password change
- Admin-only: user list, add new users (with employee ID, phone), activate/deactivate accounts

## 2. Projects (Client & Project Management)

- **Clients**: list, add, edit (Admin/Manager)
- **Projects**: list, add, edit, linked to a client, status tracking (active/completed)
- Bulk-edit projects, bulk mark-as-complete
- Export project list to Excel

## 3. Timesheets (Time Logging & Approvals)

- **My Week**: employees log daily hours against client/project, with work mode (office/remote/etc.)
- View/edit/delete own entries (day-wise grouping)
- **Approvals**: managers review and approve employee timesheets, with Excel export (overall and per-employee)
- **Project Timesheet**: hours grouped by project across employees, with Excel export
- **Open Months**: admin controls which months are open for entry (locks past months)
- **Email reminders**: send bulk or individual "please fill your timesheet" reminders to employees who haven't logged time

## 4. Claims (Expense Claims & Reimbursement)

- Employees submit expense claims with bill/receipt upload, linked to client/project
- **My Claims** (current month) and **View All Claims** (full history)
- **Review**: manager approves/rejects claims individually or in bulk, with Excel export
- **Settlement**: manager marks approved claims as paid/settled, individually or in bulk, with Excel export
- **Project-wise Claims**: claims aggregated by project, with Excel export
- **Claim Types**: admin manages the list of expense categories (add/edit/enable-disable)

## 5. Leaves

- Admin records employee leave (add/delete)

## 6. Holidays

- Admin manages the company holiday calendar (add/delete)

## 7. Dashboard (Analytics — Manager/Admin only)

- "Days filled" tracker per employee for the month (with bulk-select and send reminder)
- Charts: project-wise hours, employee-wise hours, claims by type, project-wise claim status — all with horizontal-scroll for 8+ items
- Claim summary statistics
- Export dashboard data to Excel

---

## Cross-Cutting Capabilities

- Role-based access control across all modules (Employee / Manager / Admin)
- Mobile-responsive user interface
- Security hardening (CSRF protection, access-control audit, HTTPS/HSTS configuration)
- Production deployment: Docker Compose (nginx + gunicorn + MySQL) and a non-Docker systemd+nginx path, both with Let's Encrypt SSL
