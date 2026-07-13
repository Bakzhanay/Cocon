from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("add/", views.add_task, name="add_task"),
    path("<int:task_id>/toggle/", views.toggle_task, name="toggle_task"),
    path("<int:task_id>/delete/", views.delete_task, name="delete_task"),
]
