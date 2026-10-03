from django.urls import path
from . import views

app_name = "collab"
urlpatterns = [
    path("worklist/", views.worklist, name="worklist"),
    path("worklist/scan/", views.work_scan, name="work_scan"),
    path("worklist/<int:pk>/<str:verb>/", views.work_action, name="work_action"),
    path("meetings/", views.meetings, name="meetings"),
    path("meetings/request/", views.meeting_request, name="meeting_request"),
    path("meetings/<int:pk>/room/", views.meeting_room, name="meeting_room"),
    path("meetings/<int:pk>/room/post/", views.meeting_post, name="meeting_post"),
    path("meetings/<int:pk>/room/messages/", views.meeting_messages, name="meeting_messages"),
    path("meetings/<int:pk>/respond/<str:answer>/", views.meeting_respond, name="meeting_respond"),
    path("meetings/<int:pk>/<str:action>/", views.meeting_update, name="meeting_update"),
]
