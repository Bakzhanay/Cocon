from django.contrib import admin

from .models import UserPreferences


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone", "daily_focus_goal_minutes", "weekly_focus_goal_minutes")
    search_fields = ("user__username", "user__email")
