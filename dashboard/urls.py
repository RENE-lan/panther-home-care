from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("clients/", views.clients_list, name="clients"),
    path("clients/new/", views.client_new, name="client_new"),
    path("clients/<int:pk>/", views.client_360, name="client_360"),
    path("clients/<int:pk>/family-preview/", views.family_preview, name="family_preview"),
    path("clients/<int:pk>/assessment/", views.create_assessment, name="create_assessment"),
    path("caregivers/", views.caregivers_list, name="caregivers"),
    path("personnel/", views.personnel, name="personnel"),
    path("family-portals/", views.family_portals, name="family_portals"),
    path("caregivers/new/", views.caregiver_new, name="caregiver_new"),
    path("caregivers/<int:pk>/payslip.pdf", views.payslip, name="payslip"),
    path("caregivers/<int:pk>/", views.caregiver_360, name="caregiver_360"),
    path("schedule/", views.schedule, name="schedule"),
    path("analytics/", views.analytics, name="analytics"),
    path("map/", views.operations_map, name="map"),
    path("incidents/", views.incidents_list, name="incidents"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("recruitment/", views.recruitment, name="recruitment"),
    path("settings/", views.settings_page, name="settings"),
    path("users/", views.users_list, name="users"),
    path("users/new/", views.user_new, name="user_new"),
    path("staff/", views.staff_directory, name="staff"),
    path("family-portal/", views.family_directory, name="family_directory"),
    # Caregiver self-service (open visits) + coordinator approval queue
    path("open-visits/", views.open_visits, name="open_visits"),
    path("open-visits/<int:pk>/request/", views.request_visit, name="request_visit"),
    path("my-requests/", views.my_requests, name="my_requests"),
    # EVV — caregiver visit verification (clock in/out + documentation)
    path("my-visits/", views.my_visits, name="my_visits"),
    path("my-visits/<int:pk>/checkin/", views.evv_checkin, name="evv_checkin"),
    path("my-visits/<int:pk>/document/", views.evv_document, name="evv_document"),
    path("evv/", views.evv_exceptions, name="evv_exceptions"),
    path("timesheets/", views.timesheets, name="timesheets"),
    path("recurring/", views.recurring, name="recurring"),
    # Live real-time ops
    path("live/", views.live, name="live"),
    path("api/live/", views.live_status, name="live_status"),
    # Billing & payroll
    path("billing/", views.billing, name="billing"),
    path("billing/generate/", views.generate_invoices, name="generate_invoices"),
    path("billing/<int:pk>/paid/", views.mark_invoice_paid, name="mark_invoice_paid"),
    path("billing/payroll.csv", views.payroll_csv, name="payroll_csv"),
    path("billing/invoice/new/", views.invoice_new, name="invoice_new"),
    path("billing/invoice/<int:pk>/print.pdf", views.invoice_print, name="invoice_print"),
    # AI Copilot
    path("copilot/", views.copilot, name="copilot"),
    path("copilot/ask/", views.copilot_ask, name="copilot_ask"),
    path("copilot/autofill/", views.autofill_shifts, name="autofill_shifts"),
    # Communications
    path("communications/", views.communications, name="communications"),
    # Clinical tracking (wound / care-concern manager)
    path("clinical/", views.clinical, name="clinical"),
    path("clinical/<int:pk>/", views.concern_detail, name="concern_detail"),
    # Profitability / margin calculator
    path("margin/", views.margin, name="margin"),
    # Marketing / CRM — leads pipeline
    path("leads/", views.leads, name="leads"),
    path("leads/<int:pk>/stage/", views.lead_stage, name="lead_stage"),
    path("leads/<int:pk>/convert/", views.convert_lead, name="convert_lead"),
    # Time clock (staff sign-in/out) + attendance
    path("timeclock/", views.timeclock, name="timeclock"),
    path("timeclock/punch/", views.timeclock_punch, name="timeclock_punch"),
    path("attendance/", views.attendance, name="attendance"),
    path("attendance/<int:pk>/edit/", views.edit_time, name="edit_time"),
    # EVV → hours approval → payroll
    path("hours-approval/", views.hours_approval, name="hours_approval"),
    path("hours-approval/<int:pk>/approve/", views.approve_hours, name="approve_hours"),
    path("hours-approval/approve-all/", views.approve_hours_all, name="approve_hours_all"),
    path("insights/", views.care_insights, name="insights"),
    path("automations/", views.automations, name="automations"),
    path("reports/accounting.csv", views.accounting_csv, name="accounting_csv"),
    path("calendar/<str:token>/panther.ics", views.caregiver_calendar, name="caregiver_calendar"),

    # Compliance — certification tracking + renewal alerts
    path("compliance/", views.compliance, name="compliance"),
    path("compliance/<int:pk>/remind/", views.remind_cert, name="remind_cert"),
    path("compliance/remind-all/", views.remind_all, name="remind_all"),
    path("recruitment/<int:pk>/promote/", views.promote_applicant, name="promote_applicant"),
    # Client & Family portal
    path("portal/", views.family_home, name="family_home"),
    path("portal/schedule/", views.family_schedule, name="family_schedule"),
    path("portal/reports/", views.family_reports, name="family_reports"),
    path("portal/team/", views.family_team, name="family_team"),
    path("portal/documents/", views.family_documents, name="family_documents"),
    path("portal/messages/", views.family_messages, name="family_messages"),
    path("portal/invoices/", views.family_invoices, name="family_invoices"),
    path("portal/invoices/<int:pk>/pay/", views.pay_invoice, name="pay_invoice"),
    path("requests/", views.visit_requests, name="visit_requests"),
    path("requests/<int:pk>/<str:decision>/", views.decide_request, name="decide_request"),
    path("visits/<int:pk>/", views.visit_detail, name="visit_detail"),
    path("visits/<int:pk>/approve/", views.approve_assignment, name="approve_assignment"),
    path("reports/", views.reports_list, name="reports"),
    path("reports/weekly.pdf", views.weekly_report_pdf, name="weekly_report_pdf"),
    path("reports/timesheets.csv", views.timesheet_csv, name="timesheet_csv"),
    path("reports/compliance.csv", views.compliance_csv, name="compliance_csv"),
    path("reports/<int:pk>/", views.report_detail, name="report_detail"),
    # PDF export (add ?download to force a file download instead of inline view)
    path("clients/<int:pk>/dossier.pdf", views.client_pdf, name="client_pdf"),
    path("reports/<int:pk>/report.pdf", views.report_pdf, name="report_pdf"),
    path("brief.pdf", views.brief_pdf, name="brief_pdf"),
]
