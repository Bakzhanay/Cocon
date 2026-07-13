from django.db import models
from django.conf import settings

# Create your models here.
class Topic(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    title = models.CharField(max_length=100)

    is_pinned = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "title"]

    def __str__(self):
        return self.title

class Section(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    title = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

class Subject(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="subjects",
    )

    title = models.CharField(max_length=100)

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

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
