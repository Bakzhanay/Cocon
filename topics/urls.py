from django.urls import path
from . import views

app_name = "topics"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("analytics/", views.analytics, name="analytics"),
    path(
        "dashboard/widgets/<slug:widget>/<slug:preference>/",
        views.toggle_dashboard_widget,
        name="toggle_dashboard_widget",
    ),
    path(
        "topics/add/",
        views.add_topic,
        name="add_topic",
    ),

    path(
        "topics/<int:topic_id>/edit/",
        views.edit_topic,
        name="edit_topic",
    ),

    path(
        "topics/<int:topic_id>/delete/",
        views.delete_topic,
        name="delete_topic",
    ),

    path(
        "topics/<int:topic_id>/pin/",
        views.toggle_topic_pin,
        name="toggle_topic_pin",
    ),

    path(
        "topics/<int:topic_id>/",
        views.topic_detail,
        name="topic_detail",
    ),

    path(
        "topics/<int:topic_id>/sections/add/",
        views.add_section,
        name="add_section",
    ),

    path(
        "sections/<int:section_id>/edit/",
        views.edit_section,
        name="edit_section",
    ),

    path(
        "sections/<int:section_id>/delete/",
        views.delete_section,
        name="delete_section",
    ),

    path(
        "sections/<int:section_id>/pin/",
        views.toggle_section_pin,
        name="toggle_section_pin",
    ),

    path(
        "sections/<int:section_id>/",
        views.section_detail,
        name="section_detail",
    ),

    path(
        "sections/<int:section_id>/subjects/add/",
        views.add_subject,
        name="add_subject",
    ),

    path(
        "sections/<int:section_id>/subjects/bulk-add/",
        views.bulk_add_subjects,
        name="bulk_add_subjects",
    ),

    path(
        "sections/<int:section_id>/subjects/bulk-delete/",
        views.bulk_delete_subjects,
        name="bulk_delete_subjects",
    ),

    path(
        "sections/<int:section_id>/subjects/undo/",
        views.undo_subject_action,
        name="undo_subject_action",
    ),

    path(
        "sections/<int:section_id>/subjects/redo/",
        views.redo_subject_action,
        name="redo_subject_action",
    ),

    path(
        "sections/<int:section_id>/subjects/subtitle-history/clear/",
        views.clear_subject_subtitle_history,
        name="clear_subject_subtitle_history",
    ),

    path(
        "subjects/<int:subject_id>/overview/",
        views.subject_overview,
        name="subject_overview",
    ),

    path(
        "subjects/<int:subject_id>/",
        views.subject_detail,
        name="subject_detail",
    ),

    path(
        "subjects/<int:subject_id>/edit/",
        views.edit_subject,
        name="edit_subject",
    ),

    path(
        "subjects/<int:subject_id>/delete/",
        views.delete_subject,
        name="delete_subject",
    ),

    path(
        "subjects/<int:subject_id>/toggle/",
        views.toggle_subject,
        name="toggle_subject",
    ),

    path(
        "subjects/<int:subject_id>/log-time/",
        views.log_subject_time,
        name="log_subject_time",
    ),

    path(
        "subjects/<int:subject_id>/log-time/<int:session_id>/edit/",
        views.edit_subject_time,
        name="edit_subject_time",
    ),

    path(
        "subjects/<int:subject_id>/log-time/<int:session_id>/delete/",
        views.delete_subject_time,
        name="delete_subject_time",
    ),

    path(
        "subjects/<int:subject_id>/pin/",
        views.toggle_subject_pin,
        name="toggle_subject_pin",
    ),

    path(
    "search/",
    views.search,
    name="search",
    ),

]
