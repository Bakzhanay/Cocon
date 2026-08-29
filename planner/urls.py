from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("journal/", views.task_journal, name="task_journal"),
    path("plans/", views.milestone_hub, name="milestone_hub"),
    path("add/", views.add_task, name="add_task"),
    path("<int:task_id>/edit/", views.edit_task, name="edit_task"),
    path("<int:task_id>/pin/", views.toggle_task_pin, name="toggle_task_pin"),
    path("<int:task_id>/toggle/", views.toggle_task, name="toggle_task"),
    path(
        "<int:task_id>/reflection/",
        views.update_task_reflection,
        name="update_task_reflection",
    ),
    path("<int:task_id>/delete/", views.delete_task, name="delete_task"),
    path("milestones/add/", views.add_milestone, name="add_milestone"),
    path(
        "milestones/<int:milestone_id>/toggle/",
        views.toggle_milestone,
        name="toggle_milestone",
    ),
    path(
        "milestones/<int:milestone_id>/edit/",
        views.update_milestone,
        name="update_milestone",
    ),
    path(
        "milestones/<int:milestone_id>/priority/",
        views.update_milestone_priority,
        name="update_milestone_priority",
    ),
    path(
        "milestones/<int:milestone_id>/delete/",
        views.delete_milestone,
        name="delete_milestone",
    ),
]
