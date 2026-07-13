import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from topics.models import Section, Subject, Topic

from .models import StudySession


class StudySessionApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="learner", password="test-pass-123")
        self.other_user = user_model.objects.create_user(username="other", password="test-pass-123")
        self.topic = Topic.objects.create(user=self.user, title="Biology")
        self.section = Section.objects.create(topic=self.topic, title="Cells")
        self.subject = Subject.objects.create(section=self.section, title="Mitosis")
        self.client.force_login(self.user)

    def post_json(self, name, payload):
        return self.client.post(
            reverse(name),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_completed_timer_is_linked_and_appears_in_activity(self):
        start_response = self.post_json("study:start_session", {
            "subject_id": self.subject.id,
            "section_id": self.section.id,
        })
        self.assertEqual(start_response.status_code, 200)
        session_id = start_response.json()["session_id"]

        stop_response = self.post_json("study:stop_session", {
            "session_id": session_id,
            "duration_seconds": 1500,
        })
        self.assertEqual(stop_response.status_code, 200)

        session = StudySession.objects.get(id=session_id)
        self.assertTrue(session.completed)
        self.assertEqual(session.duration_seconds, 1500)
        self.assertEqual(session.subject, self.subject)
        self.assertEqual(session.section, self.section)
        self.assertEqual(session.topic, self.topic)

        day = timezone.localdate(session.ended_at)
        activity_response = self.client.get(reverse("study:activity"), {
            "year": day.year,
            "month": day.month,
        })
        self.assertEqual(activity_response.status_code, 200)
        self.assertEqual(activity_response.json()["days"][0]["count"], 1)
        self.assertEqual(activity_response.json()["days"][0]["duration_seconds"], 1500)

    def test_user_cannot_attach_session_to_someone_elses_subject(self):
        other_topic = Topic.objects.create(user=self.other_user, title="Private")
        other_section = Section.objects.create(topic=other_topic, title="Private section")
        other_subject = Subject.objects.create(section=other_section, title="Private subject")

        response = self.post_json("study:start_session", {"subject_id": other_subject.id})

        self.assertEqual(response.status_code, 404)
        self.assertFalse(StudySession.objects.filter(user=self.user).exists())

    def test_topic_only_timer_keeps_topic_context(self):
        start_response = self.post_json("study:start_session", {
            "topic_id": self.topic.id,
            "planned_duration_seconds": 900,
        })

        self.assertEqual(start_response.status_code, 200)
        session = StudySession.objects.get(id=start_response.json()["session_id"])
        self.assertEqual(session.topic, self.topic)
        self.assertEqual(session.topic_title, self.topic.title)
        self.assertIsNone(session.section)
        self.assertIsNone(session.subject)

    def test_reset_cancels_without_counting_a_completion(self):
        start_response = self.post_json("study:start_session", {})
        session_id = start_response.json()["session_id"]

        cancel_response = self.post_json("study:cancel_session", {"session_id": session_id})

        self.assertEqual(cancel_response.status_code, 200)
        session = StudySession.objects.get(id=session_id)
        self.assertFalse(session.completed)
        self.assertEqual(session.duration_seconds, 0)
        self.assertIsNotNone(session.ended_at)

    def test_focus_panel_renders_on_the_main_app_layout(self):
        response = self.client.get(reverse("topics:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="rightSidebar"')
        self.assertContains(response, 'id="timerDisplay"')
