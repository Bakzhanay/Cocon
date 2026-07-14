from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from flashcards.models import Flashcard
from study.models import StudySession
from users.models import UserPreferences

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
        self.assertContains(response, "Continue notes")
        self.assertContains(
            response,
            reverse("topics:subject_detail", args=[self.subject.id]) + "?focus=resume",
            count=2,
        )
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

    def test_new_user_is_invited_to_start_their_first_study_session(self):
        response = self.client.get(reverse("topics:home"))

        self.assertContains(response, "Start study session")
        self.assertContains(response, "data-open-focus-panel")
        self.assertNotContains(response, "Start another session")

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

    def test_dashboard_widget_can_be_pinned_to_the_top_and_unpinned(self):
        toggle_url = reverse(
            "topics:toggle_dashboard_widget",
            args=["tasks", "pin"],
        )

        response = self.client.post(toggle_url)

        self.assertRedirects(response, reverse("topics:home"))
        preferences = UserPreferences.objects.get(user=self.user)
        self.assertEqual(preferences.dashboard_pinned_widgets, ["tasks"])

        dashboard = self.client.get(reverse("topics:home"))
        html = dashboard.content.decode()
        widget_marker = 'data-dashboard-widget="tasks"'
        self.assertEqual(html.count(widget_marker), 1)
        self.assertLess(html.index(widget_marker), html.index("Focus time"))
        self.assertContains(dashboard, "Pinned for you")

        self.client.post(toggle_url)
        preferences.refresh_from_db()
        self.assertEqual(preferences.dashboard_pinned_widgets, [])

    def test_dashboard_widget_can_be_expanded_and_compacted(self):
        toggle_url = reverse(
            "topics:toggle_dashboard_widget",
            args=["quick_notes", "expand"],
        )

        self.client.post(toggle_url)

        preferences = UserPreferences.objects.get(user=self.user)
        self.assertEqual(preferences.dashboard_expanded_widgets, ["quick_notes"])
        dashboard = self.client.get(reverse("topics:home"))
        self.assertContains(
            dashboard,
            "dashboard-panel dashboard-widget quick-notes-panel is-expanded",
        )
        self.assertContains(dashboard, "Use compact Quick notes size")

        self.client.post(toggle_url)
        preferences.refresh_from_db()
        self.assertEqual(preferences.dashboard_expanded_widgets, [])

    def test_dashboard_widget_controls_reject_unknown_values(self):
        unknown_widget = reverse(
            "topics:toggle_dashboard_widget",
            args=["calendar", "pin"],
        )
        unknown_preference = reverse(
            "topics:toggle_dashboard_widget",
            args=["tasks", "hide"],
        )

        self.assertEqual(self.client.post(unknown_widget).status_code, 400)
        self.assertEqual(self.client.post(unknown_preference).status_code, 400)
        self.assertEqual(self.client.get(unknown_widget).status_code, 405)


class FocusAnalyticsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="analyst", password="test-pass-123")
        self.topic = Topic.objects.create(
            user=self.user,
            title="IMAT",
            weekly_goal_minutes=300,
            priority="high",
        )
        self.section = Section.objects.create(
            topic=self.topic,
            title="Biology",
            weekly_goal_minutes=240,
        )
        self.subject = Subject.objects.create(
            section=self.section,
            title="Cell Biology",
            weekly_goal_minutes=120,
            priority="high",
        )
        self.client.force_login(self.user)

    def create_session(
        self,
        *,
        duration_seconds,
        topic=None,
        section=None,
        subject=None,
        activity_type="general",
        ended_at=None,
    ):
        ended_at = ended_at or timezone.now()
        return StudySession.objects.create(
            user=self.user,
            topic=topic,
            section=section,
            subject=subject,
            activity_type=activity_type,
            started_at=ended_at - timedelta(seconds=duration_seconds),
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            planned_duration_seconds=duration_seconds,
            status="completed",
            completed=True,
        )

    def test_analytics_rolls_one_session_through_each_hierarchy_level(self):
        self.create_session(
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            activity_type="notes",
            duration_seconds=600,
        )
        self.create_session(
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            activity_type="flashcards",
            duration_seconds=1200,
        )
        self.create_session(
            topic=self.topic,
            section=self.section,
            activity_type="reading",
            duration_seconds=900,
        )
        self.create_session(
            topic=self.topic,
            duration_seconds=300,
        )
        self.create_session(duration_seconds=420)

        response = self.client.get(reverse("topics:analytics"))

        self.assertEqual(response.status_code, 200)
        topic_node = response.context["tree"][0]
        section_node = topic_node["sections"][0]
        subject_node = section_node["subjects"][0]
        self.assertEqual(topic_node["seconds"], 3000)
        self.assertEqual(section_node["seconds"], 2700)
        self.assertEqual(subject_node["seconds"], 1800)
        self.assertEqual(response.context["general"]["seconds"], 420)
        self.assertEqual(response.context["total_seconds"], 3420)
        self.assertEqual(
            {item["type"]: item["seconds"] for item in subject_node["activities"]},
            {"notes": 600, "flashcards": 1200},
        )
        self.assertContains(response, "Cell Biology")
        self.assertContains(response, "Flashcards")
        self.assertContains(response, "General study")

    def test_attention_uses_elapsed_week_instead_of_full_goal(self):
        fixed_now = datetime(2026, 7, 16, 12, tzinfo=datetime_timezone.utc)
        with patch("topics.views.timezone.now", return_value=fixed_now):
            response = self.client.get(reverse("topics:analytics"))

        subject_item = next(
            item for item in response.context["attention"]
            if item["kind"] == "Subject" and item["title"] == "Cell Biology"
        )
        self.assertEqual(subject_item["status"], "behind")
        self.assertGreater(subject_item["expected_minutes"], 0)
        self.assertLess(subject_item["expected_minutes"], subject_item["goal_minutes"])
        self.assertIn("behind", subject_item["attention_message"])

    def test_attention_uses_last_activity_from_before_current_week(self):
        fixed_now = datetime(2026, 7, 16, 12, tzinfo=datetime_timezone.utc)
        self.create_session(
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            duration_seconds=600,
            ended_at=fixed_now - timedelta(days=4),
        )

        with patch("topics.views.timezone.now", return_value=fixed_now):
            response = self.client.get(reverse("topics:analytics"))

        subject_item = next(
            item for item in response.context["attention"]
            if item["kind"] == "Subject" and item["title"] == "Cell Biology"
        )
        self.assertIn("No focus for 4 days", subject_item["attention_message"])

    def test_thirty_day_period_includes_sessions_outside_current_week(self):
        self.create_session(
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            duration_seconds=1800,
            ended_at=timezone.now() - timedelta(days=10),
        )

        week_response = self.client.get(reverse("topics:analytics"), {"period": "week"})
        month_response = self.client.get(reverse("topics:analytics"), {"period": "30d"})

        self.assertEqual(week_response.context["total_seconds"], 0)
        self.assertEqual(month_response.context["total_seconds"], 1800)

    def test_parent_goals_can_be_derived_from_children(self):
        self.topic.weekly_goal_minutes = 0
        self.topic.save(update_fields=["weekly_goal_minutes"])
        self.section.weekly_goal_minutes = 0
        self.section.save(update_fields=["weekly_goal_minutes"])

        response = self.client.get(reverse("topics:analytics"))

        topic_node = response.context["tree"][0]
        section_node = topic_node["sections"][0]
        self.assertEqual(topic_node["goal_minutes"], 120)
        self.assertEqual(section_node["goal_minutes"], 120)
        self.assertTrue(topic_node["goal_is_derived"])
        self.assertTrue(section_node["goal_is_derived"])

    def test_analytics_does_not_include_another_users_focus(self):
        other = get_user_model().objects.create_user(username="other", password="test-pass-123")
        other_topic = Topic.objects.create(user=other, title="Private topic")
        StudySession.objects.create(
            user=other,
            topic=other_topic,
            started_at=timezone.now() - timedelta(minutes=20),
            ended_at=timezone.now(),
            duration_seconds=1200,
            planned_duration_seconds=1200,
            status="completed",
            completed=True,
        )

        response = self.client.get(reverse("topics:analytics"))

        self.assertNotContains(response, "Private topic")
        self.assertEqual(response.context["total_seconds"], 0)

    def test_dashboard_links_to_full_analytics(self):
        response = self.client.get(reverse("topics:home"))
        self.assertContains(response, reverse("topics:analytics"))

    def test_empty_sidebar_explains_how_to_add_the_first_topic(self):
        self.topic.delete()

        response = self.client.get(reverse("topics:home"))

        self.assertContains(response, "No topics added yet")
        self.assertContains(response, "Create your first topic")
        self.assertContains(response, reverse("topics:add_topic"))
