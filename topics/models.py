from django.db import models
from django.conf import settings

# Create your models here.
class Topic(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    title = models.CharField(max_length=100)

    is_pinned = models.BooleanField(default=False)

    weekly_goal_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Optional weekly goal. Leave at zero to derive it from sections.",
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "title"]

    def __str__(self):
        return self.title

class Section(models.Model):
    PRIORITY_CHOICES = Topic.PRIORITY_CHOICES

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    title = models.CharField(max_length=100)

    description = models.CharField(
        max_length=240,
        blank=True,
        help_text="Optional short description shown below the section name.",
    )

    is_pinned = models.BooleanField(default=False)

    weekly_goal_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Optional weekly goal. Leave at zero to derive it from subjects.",
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "title"]

    def __str__(self):
        return self.title


class ActiveSubjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class Subject(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    COLOR_CHOICES = [
        ("default", "Default"),
        ("sage", "Sage"),
        ("sky", "Sky blue"),
        ("lavender", "Lavender"),
        ("rose", "Rose"),
        ("peach", "Peach"),
        ("butter", "Soft yellow"),
        ("mint", "Mint"),
    ]

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="subjects",
    )

    title = models.CharField(max_length=100)

    description = models.CharField(
        max_length=240,
        blank=True,
        help_text="Optional short description shown below the subject name.",
    )

    is_pinned = models.BooleanField(default=False)

    color = models.CharField(
        max_length=12,
        choices=COLOR_CHOICES,
        default="default",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Отмечена ли тема как изученная
    completed = models.BooleanField(default=False)

    weekly_goal_minutes = models.PositiveIntegerField(
        default=120,
        help_text="Target study time for this subject each week.",
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
    )

    is_deleted = models.BooleanField(default=False, db_index=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveSubjectManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["completed", "-is_pinned", "created_at", "id"]

    def __str__(self):
        return self.title


class SubjectSubtitlePreset(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="subtitle_presets",
    )

    value = models.CharField(max_length=240)

    created_at = models.DateTimeField(auto_now_add=True)

    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_used_at", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "value"],
                name="unique_subject_subtitle_per_section",
            ),
        ]

    def __str__(self):
        return self.value


class SubjectHistoryAction(models.Model):
    ACTION_CHOICES = [
        ("create", "Added subjects"),
        ("delete", "Deleted subjects"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subject_history_actions",
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="subject_history_actions",
    )

    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)

    subject_ids = models.JSONField(default=list)

    is_undone = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_action_type_display()} ({len(self.subject_ids)})"
