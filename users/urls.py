from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("preferences/", views.preferences, name="preferences"),
    path("timezone/sync/", views.sync_timezone, name="sync_timezone"),
]
