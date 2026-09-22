from django.urls import path
from . import api

urlpatterns = [
    path("my-visits/", api.my_visits, name="api_my_visits"),
    path("visits/<int:pk>/check-in/", api.check_in, name="api_check_in"),
    path("visits/<int:pk>/report/", api.submit_report, name="api_submit_report"),
]
