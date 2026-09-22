from django.urls import path

from . import api

urlpatterns = [
    path("auth/login/", api.api_login, name="api_login"),
    path("auth/logout/", api.api_logout, name="api_logout"),
    path("auth/me/", api.api_me, name="api_me"),
    path("dashboard/", api.api_dashboard, name="api_dashboard"),
    path("clients/", api.api_clients, name="api_clients"),
    path("analytics/", api.api_analytics, name="api_analytics"),
]
