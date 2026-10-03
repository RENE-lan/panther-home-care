from django.urls import path
from dashboard import mobile_api as m

urlpatterns = [
    path("login/", m.login),
    path("signup/", m.signup),
    path("logout/", m.logout),
    path("me/", m.me),
    path("push-token/", m.push_token),
    path("roles/", m.roles),
    path("admin/users/", m.admin_users),
    path("admin/users/create/", m.admin_create_user),
    path("admin/users/<int:pk>/password/", m.admin_reset_password),
    path("admin/users/<int:pk>/role/", m.admin_set_role),
    path("admin/users/<int:pk>/active/", m.admin_toggle_active),

    path("dashboard/", m.dashboard),
    path("copilot/", m.copilot),
    # caregiver
    path("my-visits/", m.my_visits),
    path("cg-home/", m.cg_home),
    path("visits/<int:pk>/detail/", m.visit_detail),
    path("visits/<int:pk>/incident/", m.report_incident),
    path("personnel/", m.personnel),
    path("family-portals/", m.family_portals),

    path("visits/<int:pk>/checkin/", m.checkin),
    path("visits/<int:pk>/checkout/", m.checkout),
    path("open-visits/", m.open_visits),
    path("caregiver-alerts/", m.caregiver_alerts),
    path("assistant/", m.caregiver_assistant),
    path("open-visits/<int:pk>/request/", m.request_visit),
    path("my-requests/", m.my_requests),
    path("timesheet/", m.timesheet),
    # coordinator
    path("schedule/", m.schedule),
    path("requests/", m.requests_list),
    path("requests/<int:pk>/decide/", m.decide_request),
    path("clients/", m.clients),
    path("caregivers/", m.caregivers),
    path("visits/<int:pk>/matches/", m.visit_matches),
    path("visits/<int:pk>/assign/", m.assign_visit),
    # family
    path("family/", m.family),
    path("family/documents/", m.family_documents),
    path("family/team/", m.family_team),
    path("family/notifications/", m.family_notifications),
    path("family/visits/", m.family_visits),

    path("link-family/", m.link_family),
    path("link-demo/", m.link_demo),
    path("admin/link-family/", m.admin_link_family),
    path("messages/", m.messages),
    path("reports/", m.reports),
    path("invoices/<int:pk>/pay/", m.pay_invoice),
]
