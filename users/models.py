from django.db import models
from django.conf import settings


class UserPreferences(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_preferences",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    daily_focus_goal_minutes = models.PositiveIntegerField(default=90)
    weekly_focus_goal_minutes = models.PositiveIntegerField(default=450)
    dashboard_pinned_widgets = models.JSONField(default=list, blank=True)
    dashboard_expanded_widgets = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Preferences for {self.user}"
