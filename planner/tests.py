from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from topics.models import Section, Subject, Topic

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

    def test_study_plan_can_target_an_existing_subject(self):
        topic = Topic.objects.create(user=self.user, title="IMAT")
        section = Section.objects.create(topic=topic, title="Biology")
        subject = Subject.objects.create(section=section, title="Cells")

        response = self.client.post(reverse("planner:add_task"), {
            "task_type": "study",
            "title": "",
            "study_context": f"subject:{subject.id}",
            "target_minutes": 45,
            "activity_type": "flashcards",
            "due_date": timezone.localdate().isoformat(),
            "priority": "normal",
        })

        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(user=self.user)
        self.assertEqual(task.title, "Review Cells flashcards")
        self.assertEqual(task.subject, subject)
        self.assertEqual(task.target_minutes, 45)
        self.assertEqual(task.activity_type, "flashcards")
        self.assertFalse(task.completed)

        dashboard = self.client.get(reverse("topics:home"))
        self.assertContains(dashboard, "Study plan")
        self.assertContains(dashboard, "0 / 45 min")
        self.assertContains(dashboard, "Start focus")
        self.assertContains(dashboard, f"subject:{subject.id}")
        self.assertContains(dashboard, "data-study-context-search")
        self.assertContains(dashboard, 'aria-label="Search study items"')

    def test_user_cannot_create_plan_for_another_users_subject(self):
        topic = Topic.objects.create(user=self.other, title="Private")
        section = Section.objects.create(topic=topic, title="Private section")
        subject = Subject.objects.create(section=section, title="Private subject")

        self.client.post(reverse("planner:add_task"), {
            "task_type": "study",
            "study_context": f"subject:{subject.id}",
            "target_minutes": 25,
            "activity_type": "any",
            "priority": "normal",
        })

        self.assertFalse(Task.objects.filter(user=self.user).exists())

    def test_study_plan_requires_at_least_five_minutes(self):
        response = self.client.post(reverse("planner:add_task"), {
            "task_type": "study",
            "study_context": "general",
            "target_minutes": 4,
            "activity_type": "any",
            "priority": "normal",
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(user=self.user).exists())
