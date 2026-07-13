from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from flashcards.models import Flashcard
from study.models import StudySession

from .models import Section, Subject, Topic


class DashboardAndSearchTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="learner", password="test-pass-123")
        topic = Topic.objects.create(user=self.user, title="Science")
        section = Section.objects.create(topic=topic, title="Biology")
        self.subject = Subject.objects.create(section=section, title="Cells")
        self.card = Flashcard.objects.create(subject=self.subject, question="What is mitosis?", answer="Cell division")
        self.client.force_login(self.user)

    def test_dashboard_counts_subject_flashcards_and_focus_minutes(self):
        now = timezone.now()
        StudySession.objects.create(
            user=self.user,
            topic=self.subject.section.topic,
            subject=self.subject,
            section=self.subject.section,
            topic_title=self.subject.section.topic.title,
            subject_title=self.subject.title,
            section_title=self.subject.section.title,
            started_at=now,
            ended_at=now,
            duration_seconds=1500,
            planned_duration_seconds=1500,
            completed=True,
            status="completed",
        )
        response = self.client.get(reverse("topics:home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_minutes"], 25)
        self.assertEqual(response.context["due_flashcards"], 1)
        self.assertContains(response, "Cells")
        self.assertContains(response, "Biology 25m")
        self.assertContains(response, reverse("flashcards:due_flashcards"))

    def test_dashboard_general_session_can_open_focus_timer(self):
        now = timezone.now()
        StudySession.objects.create(
            user=self.user,
            started_at=now,
            ended_at=now,
            duration_seconds=900,
            planned_duration_seconds=900,
            completed=True,
            status="completed",
        )

        response = self.client.get(reverse("topics:home"))

        self.assertContains(response, "Unassigned focus")
        self.assertContains(response, "Start another session")
        self.assertContains(response, "data-open-focus-panel")

    def test_dashboard_chart_shows_the_last_seven_days(self):
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        StudySession.objects.create(
            user=self.user,
            topic=self.subject.section.topic,
            section=self.subject.section,
            subject=self.subject,
            started_at=yesterday - timedelta(minutes=10),
            ended_at=yesterday,
            duration_seconds=600,
            planned_duration_seconds=600,
            status="completed",
            completed=True,
        )

        response = self.client.get(reverse("topics:home"))

        chart = response.context["weekly_chart"]
        self.assertEqual(len(chart), 7)
        self.assertEqual(chart[-2]["date"], yesterday.date())
        self.assertEqual(chart[-2]["minutes"], 10)

    def test_search_finds_and_links_subject_flashcard(self):
        response = self.client.get(reverse("topics:search"), {"q": "mitosis"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is mitosis?")
        self.assertContains(response, reverse("flashcards:subject_flashcards", args=[self.subject.id]))

    def test_section_mastered_summary_updates_with_subject_checkbox(self):
        section_url = reverse("topics:section_detail", args=[self.subject.section_id])
        self.assertContains(self.client.get(section_url), "0 of 1 mastered")
        self.client.get(reverse("topics:toggle_subject", args=[self.subject.id]))
        self.assertContains(self.client.get(section_url), "1 of 1 mastered")

    def test_subject_delete_cancel_returns_to_section(self):
        response = self.client.get(reverse("topics:delete_subject", args=[self.subject.id]))
        self.assertContains(response, reverse("topics:section_detail", args=[self.subject.section_id]))

    def test_pinned_topic_moves_to_top_of_sidebar(self):
        first_topic = self.subject.section.topic
        pinned_topic = Topic.objects.create(user=self.user, title="Languages")

        response = self.client.post(
            reverse("topics:toggle_topic_pin", args=[pinned_topic.id]),
            {"next": reverse("topics:home")},
        )

        self.assertRedirects(response, reverse("topics:home"))
        pinned_topic.refresh_from_db()
        self.assertTrue(pinned_topic.is_pinned)
        dashboard = self.client.get(reverse("topics:home"))
        sidebar_topics = list(dashboard.context["sidebar_topics"])
        self.assertEqual(sidebar_topics[0], pinned_topic)
        self.assertIn(first_topic, sidebar_topics)
