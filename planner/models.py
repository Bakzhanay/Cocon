from django.conf import settings
from django.db import models


class Task(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_tasks")
    title = models.CharField(max_length=220)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    completed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["completed", "due_date", "-created_at"]

    def __str__(self):
        return self.title
