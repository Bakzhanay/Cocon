from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserPreferences


class TimezoneSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="timezone-learner",
            password="test-pass-123",
        )
        self.client.force_login(self.user)

    def test_browser_timezone_updates_automatic_preferences(self):
        response = self.client.post(
            reverse("users:sync_timezone"),
            {"timezone": "Asia/Almaty"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])
        self.assertEqual(
            UserPreferences.objects.get(user=self.user).timezone,
            "Asia/Almaty",
        )

    def test_manual_timezone_is_not_overwritten(self):
        UserPreferences.objects.create(
            user=self.user,
            timezone="Europe/London",
            auto_detect_timezone=False,
        )

        response = self.client.post(
            reverse("users:sync_timezone"),
            {"timezone": "Asia/Almaty"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])
        self.assertEqual(
            UserPreferences.objects.get(user=self.user).timezone,
            "Europe/London",
        )

    def test_unknown_timezone_is_rejected(self):
        response = self.client.post(
            reverse("users:sync_timezone"),
            {"timezone": "Not/A-Timezone"},
        )

        self.assertEqual(response.status_code, 400)

# Create your tests here.
