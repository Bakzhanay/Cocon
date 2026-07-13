from django.contrib import admin

from .models import StudySession


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "section",
        "subject",
        "started_at",
        "ended_at",
        "duration_seconds",
        "status",
        "activity_type",
    )

    list_filter = (
        "section",
        "subject",
        "status",
        "activity_type",
    )

    search_fields = (
        "user__username",
    )
