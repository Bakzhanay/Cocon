from django.db import models
from django.contrib.auth.models import User

from topics.models import Section, Subject, Topic

class StudySession(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    ACTIVITY_CHOICES = [
        ("general", "General study"),
        ("notes", "Notes"),
        ("flashcards", "Flashcards"),
        ("reading", "Reading"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    duration_seconds = models.PositiveIntegerField(
        default=0,
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    planned_duration_seconds = models.PositiveIntegerField(default=0)

    paused_seconds = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
    )

    activity_type = models.CharField(
        max_length=12,
        choices=ACTIVITY_CHOICES,
        default="general",
    )

    topic_title = models.CharField(max_length=100, blank=True)

    section_title = models.CharField(max_length=100, blank=True)

    subject_title = models.CharField(max_length=100, blank=True)

    completed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):

        if self.subject:
            return f"{self.subject.title} ({self.duration_seconds}s)"

        if self.section:
            return f"{self.section.title} ({self.duration_seconds}s)"

        if self.topic:
            return f"{self.topic.title} ({self.duration_seconds}s)"

        return f"{self.duration_seconds}s"
