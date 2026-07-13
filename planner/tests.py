from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Task


class PlannerTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="planner", password="test-pass-123")
        self.other = user_model.objects.create_user(username="other-planner", password="test-pass-123")
        self.client.force_login(self.user)

    def test_task_lifecycle_and_calendar_marker(self):
        due_date = timezone.localdate() + timedelta(days=1)
        response = self.client.post(reverse("planner:add_task"), {
            "title": "Review biology",
            "due_date": due_date.isoformat(),
            "priority": "high",
        })
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(user=self.user)

        activity = self.client.get(reverse("study:activity"), {
            "year": due_date.year,
            "month": due_date.month,
        }).json()
        self.assertEqual(activity["tasks"][0]["date"], due_date.isoformat())

        self.client.post(reverse("planner:toggle_task", args=[task.id]))
        task.refresh_from_db()
        self.assertTrue(task.completed)

    def test_user_cannot_toggle_another_users_task(self):
        task = Task.objects.create(user=self.other, title="Private")
        response = self.client.post(reverse("planner:toggle_task", args=[task.id]))
        self.assertEqual(response.status_code, 404)
