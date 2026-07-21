from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    ACTIVITY_CHOICES = [
        ("any", "Any study activity"),
        ("general", "General study"),
        ("notes", "Notes"),
        ("flashcards", "Flashcards"),
        ("reading", "Reading"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_tasks")
    title = models.CharField(max_length=220)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    completed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    topic = models.ForeignKey(
        "topics.Topic",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planned_tasks",
    )
    section = models.ForeignKey(
        "topics.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planned_tasks",
    )
    subject = models.ForeignKey(
        "topics.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planned_tasks",
    )
    activity_type = models.CharField(
        max_length=12,
        choices=ACTIVITY_CHOICES,
        default="any",
    )
    target_minutes = models.PositiveIntegerField(default=0)
    focused_seconds = models.PositiveIntegerField(default=0)
    completed_by_focus = models.BooleanField(default=False)

    class Meta:
        ordering = ["completed", "due_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_study_task(self):
        return self.target_minutes > 0

    @property
    def target_seconds(self):
        return self.target_minutes * 60

    @property
    def progress_percent(self):
        if not self.target_seconds:
            return 0
        return min(100, round(self.focused_seconds / self.target_seconds * 100))

    @property
    def focused_minutes(self):
        return round(self.focused_seconds / 60)

    @property
    def remaining_minutes(self):
        remaining_seconds = max(0, self.target_seconds - self.focused_seconds)
        return (remaining_seconds + 59) // 60

    @property
    def study_context_label(self):
        if self.subject_id:
            return self.subject.title if self.subject else "Deleted subject"
        if self.section_id:
            return self.section.title if self.section else "Deleted section"
        if self.topic_id:
            return self.topic.title if self.topic else "Deleted topic"
        return "General study"

    def mark_manually(self, completed):
        self.completed = completed
        self.completed_at = timezone.now() if completed else None
        self.completed_by_focus = False
