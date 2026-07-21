from django.urls import path

from . import views

app_name = "study"

urlpatterns = [
    path("start/", views.start_session, name="start_session"),
    path("context/", views.sync_session_context, name="sync_session_context"),
    path("stop/", views.stop_session, name="stop_session"),
    path("cancel/", views.cancel_session, name="cancel_session"),
    path("activity/", views.activity, name="activity"),
]
