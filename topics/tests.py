from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from flashcards.models import Flashcard
from notes.models import Note
from study.models import StudySession, StudySessionSegment
from users.models import UserPreferences

from .models import Section, Subject, SubjectSubtitlePreset, Topic


class DashboardAndSearchTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="learner", password="test-pass-123")
        self.topic = Topic.objects.create(user=self.user, title="Science")
        self.section = Section.objects.create(topic=self.topic, title="Biology")
        self.subject = Subject.objects.create(section=self.section, title="Cells")
        self.card = Flashcard.objects.create(subject=self.subject, question="What is mitosis?", answer="Cell division")
        self.client.force_login(self.user)

    def create_completed_focus(
        self,
        duration_seconds,
        *,
        topic=None,
        section=None,
        subject=None,
        activity_type="general",
    ):
        if subject:
            section = subject.section
            topic = section.topic
        elif section:
            topic = section.topic
        ended_at = timezone.now()
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
            completed=True,
            status="completed",
        )

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
        self.assertContains(response, "Start studying")
        self.assertContains(
            response,
            reverse("topics:subject_overview", args=[self.subject.id]) + "?focus=resume",
            count=1,
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
        self.assertContains(response, "Start studying")
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

    def test_dashboard_focus_by_area_uses_all_completed_time(self):
        ended_at = timezone.now() - timedelta(days=15)
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            started_at=ended_at - timedelta(minutes=50),
            ended_at=ended_at,
            duration_seconds=3000,
            planned_duration_seconds=3000,
            status="completed",
            completed=True,
        )

        response = self.client.get(reverse("topics:home"))

        topic_focus = response.context["focus_by_topic"][0]
        self.assertEqual(response.context["week_minutes"], 0)
        self.assertEqual(topic_focus["minutes"], 50)
        self.assertEqual(topic_focus["detail"], "Biology 50m")
        self.assertContains(response, "Balance &middot; all time", html=True)

    def test_dashboard_rhythm_can_show_last_thirty_days(self):
        ended_at = timezone.now() - timedelta(days=10)
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            started_at=ended_at - timedelta(minutes=20),
            ended_at=ended_at,
            duration_seconds=1200,
            planned_duration_seconds=1200,
            status="completed",
            completed=True,
        )

        response = self.client.get(reverse("topics:home"), {"rhythm": "30d"})

        chart = response.context["rhythm_chart"]
        chart_by_date = {item["date"]: item["minutes"] for item in chart}
        self.assertEqual(response.context["rhythm_period"], "30d")
        self.assertEqual(response.context["rhythm_total_minutes"], 20)
        self.assertEqual(len(chart), 30)
        self.assertEqual(chart_by_date[ended_at.date()], 20)
        active_bucket = next(item for item in chart if item["date"] == ended_at.date())
        self.assertEqual(active_bucket["breakdown"][0]["label"], "Science")
        self.assertEqual(active_bucket["breakdown"][0]["duration"], "20 min")

    def test_dashboard_rhythm_breakdown_uses_session_segments(self):
        languages = Topic.objects.create(user=self.user, title="Languages")
        ended_at = timezone.now() - timedelta(days=2)
        session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            topic_title=self.topic.title,
            started_at=ended_at - timedelta(minutes=25),
            ended_at=ended_at,
            duration_seconds=1500,
            planned_duration_seconds=1500,
            status="completed",
            completed=True,
        )
        StudySessionSegment.objects.create(
            session=session,
            topic=self.topic,
            topic_title=self.topic.title,
            activity_type="reading",
            duration_seconds=600,
        )
        StudySessionSegment.objects.create(
            session=session,
            topic=languages,
            topic_title=languages.title,
            activity_type="general",
            started_offset_seconds=600,
            duration_seconds=900,
        )

        response = self.client.get(reverse("topics:home"), {"rhythm": "30d"})

        bucket = next(
            item for item in response.context["rhythm_chart"]
            if item["date"] == ended_at.date()
        )
        breakdown = {item["label"]: item["seconds"] for item in bucket["breakdown"]}
        self.assertEqual(bucket["minutes"], 25)
        self.assertEqual(breakdown, {"Languages": 900, "Science": 600})

    def test_dashboard_rhythm_can_show_last_twelve_months(self):
        ended_at = timezone.now() - timedelta(days=180)
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            started_at=ended_at - timedelta(minutes=35),
            ended_at=ended_at,
            duration_seconds=2100,
            planned_duration_seconds=2100,
            status="completed",
            completed=True,
        )

        response = self.client.get(reverse("topics:home"), {"rhythm": "year"})

        self.assertEqual(response.context["rhythm_period"], "year")
        self.assertEqual(response.context["rhythm_total_minutes"], 35)
        self.assertEqual(len(response.context["rhythm_chart"]), 12)

    def test_dashboard_uses_local_timezone_for_week_boundary(self):
        preferences, _ = UserPreferences.objects.get_or_create(user=self.user)
        preferences.timezone = "Asia/Almaty"
        preferences.save(update_fields=["timezone"])
        session_end = datetime(2026, 7, 19, 20, 22, tzinfo=datetime_timezone.utc)
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            started_at=session_end - timedelta(minutes=15),
            ended_at=session_end,
            duration_seconds=900,
            planned_duration_seconds=900,
            status="completed",
            completed=True,
        )
        fixed_now = datetime(2026, 7, 21, 12, 17, tzinfo=datetime_timezone.utc)

        with patch("topics.views.timezone.now", return_value=fixed_now):
            response = self.client.get(reverse("topics:home"))
            analytics_response = self.client.get(reverse("topics:analytics"))

        self.assertEqual(response.context["week_minutes"], 15)
        self.assertEqual(response.context["week_sessions_count"], 1)
        self.assertEqual(response.context["streak"], 1)
        chart_by_date = {item["date"]: item["minutes"] for item in response.context["weekly_chart"]}
        self.assertEqual(chart_by_date[datetime(2026, 7, 20).date()], 15)
        self.assertEqual(chart_by_date[datetime(2026, 7, 19).date()], 0)
        self.assertEqual(analytics_response.context["total_seconds"], 900)

    def test_search_finds_and_links_subject_flashcard(self):
        response = self.client.get(reverse("topics:search"), {"q": "mitosis"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is mitosis?")
        self.assertContains(response, reverse("flashcards:subject_flashcards", args=[self.subject.id]))

    def test_section_and_subject_descriptions_are_created_and_displayed(self):
        section_description = "Living systems and their organization"
        subject_description = "The cell as the basis of life"

        section_response = self.client.post(
            reverse("topics:add_section", args=[self.topic.id]),
            {
                "title": "Foundations",
                "description": section_description,
                "weekly_goal_minutes": 0,
                "priority": "normal",
            },
        )
        section = Section.objects.get(topic=self.topic, title="Foundations")
        self.assertRedirects(
            section_response,
            reverse("topics:topic_detail", args=[self.topic.id]),
        )

        subject_response = self.client.post(
            reverse("topics:add_subject", args=[section.id]),
            {
                "title": "Cell",
                "description": subject_description,
                "color": "sage",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )
        subject = Subject.objects.get(section=section, title="Cell")
        self.assertRedirects(
            subject_response,
            reverse("topics:section_detail", args=[section.id]),
        )

        self.assertContains(
            self.client.get(reverse("topics:topic_detail", args=[self.topic.id])),
            section_description,
        )
        section_page = self.client.get(reverse("topics:section_detail", args=[section.id]))
        self.assertContains(section_page, section_description)
        self.assertContains(section_page, subject_description)
        self.assertContains(section_page, "subject-card subject-color-sage")
        self.assertContains(
            self.client.get(reverse("topics:subject_detail", args=[subject.id])),
            subject_description,
        )

    def test_learning_pages_show_the_full_breadcrumb_path(self):
        dashboard_url = reverse("topics:home")
        topic_url = reverse("topics:topic_detail", args=[self.topic.id])
        section_url = reverse("topics:section_detail", args=[self.section.id])
        subject_url = reverse("topics:subject_overview", args=[self.subject.id])

        topic_response = self.client.get(topic_url)
        self.assertContains(topic_response, 'aria-label="Learning path"')
        self.assertContains(
            topic_response,
            f'href="{dashboard_url}" class="learning-breadcrumb-link"',
        )
        self.assertContains(
            topic_response,
            '<span class="learning-breadcrumb-current" aria-current="page">Science</span>',
            html=True,
        )

        section_response = self.client.get(section_url)
        self.assertContains(
            section_response,
            f'href="{topic_url}" class="learning-breadcrumb-link"',
        )
        self.assertContains(
            section_response,
            '<span class="learning-breadcrumb-current" aria-current="page">Biology</span>',
            html=True,
        )

        overview_response = self.client.get(subject_url)
        self.assertContains(
            overview_response,
            f'href="{section_url}" class="learning-breadcrumb-link"',
        )
        self.assertContains(
            overview_response,
            '<span class="learning-breadcrumb-current" aria-current="page">Cells</span>',
            html=True,
        )

        notes_response = self.client.get(
            reverse("topics:subject_detail", args=[self.subject.id])
        )
        self.assertContains(
            notes_response,
            f'href="{subject_url}" class="learning-breadcrumb-link"',
        )
        self.assertContains(
            notes_response,
            '<span class="learning-breadcrumb-current" aria-current="page">Notes</span>',
            html=True,
        )

    def test_section_and_subject_descriptions_can_be_edited(self):
        section_description = "Core biological principles"
        subject_description = "Structure and function of cells"

        self.client.post(
            reverse("topics:edit_section", args=[self.section.id]),
            {
                "title": self.section.title,
                "description": section_description,
                "weekly_goal_minutes": 0,
                "priority": "normal",
            },
        )
        self.client.post(
            reverse("topics:edit_subject", args=[self.subject.id]),
            {
                "title": self.subject.title,
                "description": subject_description,
                "color": "lavender",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )

        self.section.refresh_from_db()
        self.subject.refresh_from_db()
        self.assertEqual(self.section.description, section_description)
        self.assertEqual(self.subject.description, subject_description)
        self.assertEqual(self.subject.color, "lavender")

    def test_subject_card_color_rejects_unknown_palette_value(self):
        response = self.client.post(
            reverse("topics:edit_subject", args=[self.subject.id]),
            {
                "title": self.subject.title,
                "description": self.subject.description,
                "color": "neon",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.color, "default")

    def test_section_page_exposes_subject_status_and_color_filters(self):
        self.subject.color = "sky"
        self.subject.completed = True
        self.subject.save(update_fields=["color", "completed"])

        response = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )

        self.assertEqual(response.context["subject_color_choices"], Subject.COLOR_CHOICES)
        self.assertContains(response, 'id="subjectStatusFilter"')
        self.assertContains(response, 'id="subjectColorFilter"')
        self.assertContains(response, 'id="subjectOrderFilter"')
        self.assertContains(response, '<option value="sky">Sky blue</option>', html=True)
        self.assertContains(response, 'data-subject-status="mastered"')
        self.assertContains(response, 'data-subject-color="sky"')
        self.assertContains(response, 'data-subject-pinned="false"')
        self.assertContains(response, 'data-subject-title="cells"')
        self.assertContains(response, "js/subject_filters.js?v=2")

    def test_focus_statistics_roll_up_from_subject_to_section_and_topic(self):
        self.create_completed_focus(
            1500,
            subject=self.subject,
            activity_type="notes",
        )
        self.create_completed_focus(
            600,
            subject=self.subject,
            activity_type="flashcards",
        )
        self.create_completed_focus(300, section=self.section)
        self.create_completed_focus(120, topic=self.topic)

        topic_page = self.client.get(
            reverse("topics:topic_detail", args=[self.topic.id])
        )
        section_card = topic_page.context["sections"][0]
        self.assertEqual(topic_page.context["topic"].focus_duration, "42 min")
        self.assertEqual(section_card.focus_duration, "40 min")
        self.assertContains(topic_page, "Show statistics")
        self.assertContains(topic_page, "js/focus_stats.js?v=1")

        section_page = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )
        subject_card = section_page.context["subjects"][0]
        self.assertEqual(section_page.context["section"].focus_duration, "40 min")
        self.assertEqual(subject_card.focus_duration, "35 min")
        self.assertEqual(subject_card.notes_focus_duration, "25 min")
        self.assertEqual(subject_card.flashcards_focus_duration, "10 min")
        self.assertContains(section_page, "Show statistics")
        self.assertContains(
            section_page,
            reverse("topics:subject_overview", args=[self.subject.id]),
        )

    def test_subject_overview_tracks_general_subject_study_separately(self):
        self.create_completed_focus(900, subject=self.subject)
        self.create_completed_focus(
            600,
            subject=self.subject,
            activity_type="notes",
        )
        self.create_completed_focus(
            300,
            subject=self.subject,
            activity_type="flashcards",
        )

        response = self.client.get(
            reverse("topics:subject_overview", args=[self.subject.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_activity_type"], "general")
        self.assertEqual(response.context["subject"].focus_duration, "30 min")
        self.assertEqual(response.context["subject"].subject_study_duration, "15 min")
        self.assertEqual(response.context["subject"].notes_focus_duration, "10 min")
        self.assertEqual(response.context["subject"].flashcards_focus_duration, "5 min")
        self.assertContains(response, "Start focus on Cells")
        self.assertContains(response, reverse("topics:subject_detail", args=[self.subject.id]))
        self.assertContains(
            response,
            reverse("flashcards:subject_flashcards", args=[self.subject.id]),
        )
        self.assertContains(response, "Tracking Science / Biology / Cells")

    def test_subjects_keep_the_order_they_were_created(self):
        second_subject = Subject.objects.create(section=self.section, title="Zoology")
        third_subject = Subject.objects.create(section=self.section, title="Anatomy")

        section_page = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )

        self.assertEqual(
            list(section_page.context["subjects"]),
            [self.subject, second_subject, third_subject],
        )

    def test_search_finds_section_and_subject_descriptions(self):
        self.section.description = "Molecular foundations"
        self.section.save(update_fields=["description"])
        self.subject.description = "The cell as the basis of life"
        self.subject.save(update_fields=["description"])

        section_results = self.client.get(reverse("topics:search"), {"q": "molecular"})
        subject_results = self.client.get(reverse("topics:search"), {"q": "basis of life"})

        self.assertContains(section_results, self.section.title)
        self.assertContains(subject_results, self.subject.title)

    def test_section_mastered_summary_updates_with_subject_checkbox(self):
        section_url = reverse("topics:section_detail", args=[self.subject.section_id])
        self.assertContains(self.client.get(section_url), "0 of 1 mastered")
        self.client.get(reverse("topics:toggle_subject", args=[self.subject.id]))
        self.assertContains(self.client.get(section_url), "1 of 1 mastered")

    def test_mastering_subject_only_changes_completion_state(self):
        response = self.client.get(
            reverse("topics:toggle_subject", args=[self.subject.id]),
            follow=True,
        )

        self.subject.refresh_from_db()
        self.assertTrue(self.subject.completed)
        self.assertNotContains(response, f"Add time spent on {self.subject.title}?")
        self.assertFalse(StudySession.objects.exists())

    def test_manual_subject_time_is_saved_as_completed_hierarchical_focus(self):
        response = self.client.post(
            reverse("topics:log_subject_time", args=[self.subject.id]),
            {
                "focus_date": timezone.localdate().isoformat(),
                "hours": "1",
                "minutes": "30",
            },
        )

        self.assertRedirects(
            response,
            reverse("topics:subject_overview", args=[self.subject.id])
            + "?manage_time=1#manual-focus-time",
        )
        session = StudySession.objects.get(entry_source="manual")
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.topic, self.topic)
        self.assertEqual(session.section, self.section)
        self.assertEqual(session.subject, self.subject)
        self.assertEqual(session.activity_type, "general")
        self.assertEqual(session.duration_seconds, 90 * 60)
        self.assertEqual(session.ended_at - session.started_at, timedelta(minutes=90))
        self.assertTrue(session.completed)
        self.assertEqual(session.status, "completed")

        section_page = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )
        self.assertEqual(section_page.context["section"].focus_duration, "1 h 30 min")
        self.assertEqual(
            section_page.context["subjects"][0].focus_duration,
            "1 h 30 min",
        )

        dashboard = self.client.get(reverse("topics:home"))
        self.assertContains(dashboard, "Manually logged")
        self.assertEqual(dashboard.context["today_minutes"], 90)

    def test_manual_subject_time_rejects_invalid_values(self):
        log_url = reverse("topics:log_subject_time", args=[self.subject.id])

        response = self.client.post(
            log_url,
            {
                "focus_date": timezone.localdate().isoformat(),
                "hours": "0",
                "minutes": "60",
            },
            follow=True,
        )

        self.assertFalse(StudySession.objects.exists())
        self.assertContains(response, "Minutes must be from 0 to 59")
        self.assertTrue(response.context["manage_time_open"])

    def test_manual_subject_time_can_be_edited_and_deleted(self):
        ended_at = timezone.now() - timedelta(days=2)
        session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            started_at=ended_at - timedelta(hours=2),
            ended_at=ended_at,
            duration_seconds=2 * 60 * 60,
            status="completed",
            completed=True,
            activity_type="general",
            entry_source="manual",
        )

        edit_response = self.client.post(
            reverse(
                "topics:edit_subject_time",
                args=[self.subject.id, session.id],
            ),
            {
                "focus_date": timezone.localdate().isoformat(),
                "hours": "0",
                "minutes": "45",
            },
        )

        self.assertRedirects(
            edit_response,
            reverse("topics:subject_overview", args=[self.subject.id])
            + "?manage_time=1#manual-focus-time",
        )
        session.refresh_from_db()
        self.assertEqual(session.duration_seconds, 45 * 60)
        overview = self.client.get(
            reverse("topics:subject_overview", args=[self.subject.id])
        )
        self.assertContains(overview, "45 min")
        self.assertContains(overview, "Manage focused time")

        delete_response = self.client.post(
            reverse(
                "topics:delete_subject_time",
                args=[self.subject.id, session.id],
            )
        )
        self.assertRedirects(
            delete_response,
            reverse("topics:subject_overview", args=[self.subject.id])
            + "?manage_time=1#manual-focus-time",
        )
        self.assertFalse(StudySession.objects.filter(id=session.id).exists())

    def test_timer_session_cannot_be_edited_as_manual_time(self):
        session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            started_at=timezone.now() - timedelta(minutes=25),
            ended_at=timezone.now(),
            duration_seconds=25 * 60,
            status="completed",
            completed=True,
            entry_source="timer",
        )

        response = self.client.post(
            reverse(
                "topics:edit_subject_time",
                args=[self.subject.id, session.id],
            ),
            {
                "focus_date": timezone.localdate().isoformat(),
                "hours": "1",
                "minutes": "0",
            },
        )

        self.assertEqual(response.status_code, 404)
        session.refresh_from_db()
        self.assertEqual(session.duration_seconds, 25 * 60)

    def test_manual_subject_time_cannot_be_added_to_another_users_subject(self):
        other_user = get_user_model().objects.create_user(
            username="private-learner",
            password="test-pass-456",
        )
        other_topic = Topic.objects.create(user=other_user, title="Private")
        other_section = Section.objects.create(topic=other_topic, title="Private section")
        other_subject = Subject.objects.create(
            section=other_section,
            title="Private subject",
        )

        response = self.client.post(
            reverse("topics:log_subject_time", args=[other_subject.id]),
            {"hours": "1", "minutes": "0"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(StudySession.objects.exists())

    def test_unmastering_subject_does_not_delete_logged_time_or_reopen_prompt(self):
        self.subject.completed = True
        self.subject.save(update_fields=["completed"])
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            started_at=timezone.now() - timedelta(minutes=20),
            ended_at=timezone.now(),
            duration_seconds=20 * 60,
            status="completed",
            completed=True,
            entry_source="manual",
        )

        response = self.client.get(
            reverse("topics:toggle_subject", args=[self.subject.id]),
            follow=True,
        )

        self.subject.refresh_from_db()
        self.assertFalse(self.subject.completed)
        self.assertEqual(StudySession.objects.count(), 1)

    def test_mastered_subject_moves_below_active_subjects_even_when_pinned(self):
        active_subject = Subject.objects.create(section=self.section, title="Organelles")
        self.subject.is_pinned = True
        self.subject.save(update_fields=["is_pinned"])

        self.client.get(reverse("topics:toggle_subject", args=[self.subject.id]))

        section_page = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )
        self.assertEqual(
            list(section_page.context["subjects"]),
            [active_subject, self.subject],
        )

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

    def test_pinned_section_moves_to_top_of_topic_and_sidebar(self):
        pinned_section = Section.objects.create(topic=self.topic, title="Zoology")
        topic_url = reverse("topics:topic_detail", args=[self.topic.id])

        response = self.client.post(
            reverse("topics:toggle_section_pin", args=[pinned_section.id]),
            {"next": topic_url},
        )

        self.assertRedirects(response, topic_url)
        pinned_section.refresh_from_db()
        self.assertTrue(pinned_section.is_pinned)

        topic_page = self.client.get(topic_url)
        self.assertEqual(list(topic_page.context["sections"])[0], pinned_section)
        self.assertContains(topic_page, f"Unpin {pinned_section.title}")

        sidebar_topic = next(
            topic
            for topic in topic_page.context["sidebar_topics"]
            if topic.id == self.topic.id
        )
        self.assertEqual(list(sidebar_topic.sections.all())[0], pinned_section)

    def test_pinned_subject_moves_to_top_of_section(self):
        pinned_subject = Subject.objects.create(section=self.section, title="Zoology")
        section_url = reverse("topics:section_detail", args=[self.section.id])

        response = self.client.post(
            reverse("topics:toggle_subject_pin", args=[pinned_subject.id]),
            {"next": section_url},
        )

        self.assertRedirects(response, section_url)
        pinned_subject.refresh_from_db()
        self.assertTrue(pinned_subject.is_pinned)

        section_page = self.client.get(section_url)
        self.assertEqual(list(section_page.context["subjects"])[0], pinned_subject)
        self.assertContains(section_page, f"Unpin {pinned_subject.title}")

    def test_section_and_subject_pins_require_post_and_owner(self):
        user_model = get_user_model()
        other_user = user_model.objects.create_user(
            username="other-learner",
            password="test-pass-456",
        )
        other_topic = Topic.objects.create(user=other_user, title="Private")
        other_section = Section.objects.create(topic=other_topic, title="Private section")
        other_subject = Subject.objects.create(section=other_section, title="Private subject")

        self.assertEqual(
            self.client.get(reverse("topics:toggle_section_pin", args=[self.section.id])).status_code,
            405,
        )
        self.assertEqual(
            self.client.get(reverse("topics:toggle_subject_pin", args=[self.subject.id])).status_code,
            405,
        )
        self.assertEqual(
            self.client.post(reverse("topics:toggle_section_pin", args=[other_section.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("topics:toggle_subject_pin", args=[other_subject.id])).status_code,
            404,
        )

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


class BulkSubjectCreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="bulk-learner",
            password="test-pass-123",
        )
        self.topic = Topic.objects.create(user=self.user, title="IMAT")
        self.section = Section.objects.create(
            topic=self.topic,
            title="Logical reasoning",
        )
        self.client.force_login(self.user)

    def test_bulk_page_is_available_from_section(self):
        section_page = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )
        bulk_url = reverse("topics:bulk_add_subjects", args=[self.section.id])

        self.assertContains(section_page, bulk_url)
        response = self.client.get(bulk_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bulk add subjects")
        self.assertContains(response, "Paste only the subject names")
        self.assertContains(response, "Common subtitle")
        self.assertContains(response, "Check the cards before adding")

    def test_bulk_add_parses_groups_inline_subtitles_and_preserves_order(self):
        response = self.client.post(
            reverse("topics:bulk_add_subjects", args=[self.section.id]),
            {
                "source_entries": (
                    "Critical Thinking:\n"
                    "- Assessing the impact of additional evidence\n"
                    "- Detecting reasoning errors\n\n"
                    "**Problem Solving**\n"
                    "• Interpreting data in a table or graph\n"
                    "Custom practice | Mixed review"
                ),
                "color": "sky",
                "weekly_goal_minutes": 90,
                "priority": "high",
            },
            follow=True,
        )

        self.assertContains(response, "Added 4 subject(s).")
        subjects = list(self.section.subjects.order_by("created_at", "id"))
        self.assertEqual(
            [subject.title for subject in subjects],
            [
                "Assessing the impact of additional evidence",
                "Detecting reasoning errors",
                "Interpreting data in a table or graph",
                "Custom practice",
            ],
        )
        self.assertEqual(
            [subject.description for subject in subjects],
            [
                "Critical Thinking",
                "Critical Thinking",
                "Problem Solving",
                "Mixed review",
            ],
        )
        self.assertTrue(all(subject.color == "sky" for subject in subjects))
        self.assertTrue(all(subject.weekly_goal_minutes == 90 for subject in subjects))
        self.assertTrue(all(subject.priority == "high" for subject in subjects))
        self.assertEqual(
            set(self.section.subtitle_presets.values_list("value", flat=True)),
            {"Critical Thinking", "Problem Solving", "Mixed review"},
        )

    def test_plain_heading_before_bullets_becomes_a_subtitle(self):
        self.client.post(
            reverse("topics:bulk_add_subjects", args=[self.section.id]),
            {
                "source_entries": "Problem Solving\n○ Working out financial problems\n○ Using spatial reasoning",
                "color": "default",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )

        self.assertEqual(self.section.subjects.count(), 2)
        self.assertFalse(
            self.section.subjects.filter(title="Problem Solving").exists()
        )
        self.assertEqual(
            set(self.section.subjects.values_list("description", flat=True)),
            {"Problem Solving"},
        )

    def test_bulk_add_skips_existing_and_repeated_names_case_insensitively(self):
        Subject.objects.create(section=self.section, title="Cells")

        response = self.client.post(
            reverse("topics:bulk_add_subjects", args=[self.section.id]),
            {
                "source_entries": "cells\nCELLS\nNew subject",
                "color": "default",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
            follow=True,
        )

        self.assertContains(response, "Added 1 subject(s). Skipped 2 duplicate(s).")
        self.assertEqual(self.section.subjects.count(), 2)
        self.assertTrue(
            self.section.subjects.filter(title="New subject").exists()
        )

    def test_saved_subtitle_is_suggested_and_can_be_cleared(self):
        add_url = reverse("topics:add_subject", args=[self.section.id])
        self.client.post(
            add_url,
            {
                "title": "Matching arguments",
                "description": "Critical Thinking",
                "color": "sage",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )

        self.assertTrue(
            SubjectSubtitlePreset.objects.filter(
                section=self.section,
                value="Critical Thinking",
            ).exists()
        )
        form_page = self.client.get(add_url)
        self.assertContains(form_page, 'list="subjectSubtitleHistory"')
        self.assertContains(form_page, '<option value="Critical Thinking">')
        self.assertContains(form_page, "Clear saved subtitles")

        response = self.client.post(
            reverse(
                "topics:clear_subject_subtitle_history",
                args=[self.section.id],
            ),
            {"next": add_url},
        )

        self.assertRedirects(response, add_url)
        self.assertFalse(self.section.subtitle_presets.exists())
        self.assertEqual(
            self.section.subjects.get(title="Matching arguments").description,
            "Critical Thinking",
        )

    def test_preview_payload_supports_common_and_individual_subtitles(self):
        self.client.post(
            reverse("topics:bulk_add_subjects", args=[self.section.id]),
            {
                "source_entries": "1. Photosynthesis\n2. Plant cells\n3. Food chains",
                "entries": (
                    "Photosynthesis\n"
                    "Plant cells | Cell structures\n"
                    "Food chains"
                ),
                "preview_ready": "1",
                "common_subtitle": "Biology basics",
                "color": "mint",
                "weekly_goal_minutes": 75,
                "priority": "normal",
            },
        )

        subjects = list(self.section.subjects.order_by("created_at", "id"))
        self.assertEqual(
            [subject.title for subject in subjects],
            ["Photosynthesis", "Plant cells", "Food chains"],
        )
        self.assertEqual(
            [subject.description for subject in subjects],
            ["Biology basics", "Cell structures", "Biology basics"],
        )

    def test_bulk_delete_can_be_undone_and_redone_without_losing_content(self):
        first = Subject.objects.create(section=self.section, title="First")
        second = Subject.objects.create(section=self.section, title="Second")
        third = Subject.objects.create(section=self.section, title="Keep")
        note = Note.objects.create(
            owner=self.user,
            subject=first,
            title="Saved note",
            content="Important content",
        )
        flashcard = Flashcard.objects.create(
            subject=first,
            question="Question",
            answer="Answer",
        )

        response = self.client.post(
            reverse("topics:bulk_delete_subjects", args=[self.section.id]),
            {"subject_ids": [first.id, second.id]},
        )
        self.assertRedirects(
            response,
            reverse("topics:section_detail", args=[self.section.id]),
        )
        self.assertEqual(list(self.section.subjects.values_list("id", flat=True)), [third.id])
        self.assertTrue(Subject.all_objects.filter(id=first.id, is_deleted=True).exists())
        self.assertTrue(Note.objects.filter(id=note.id).exists())
        self.assertTrue(Flashcard.objects.filter(id=flashcard.id).exists())

        self.client.post(reverse("topics:undo_subject_action", args=[self.section.id]))
        self.assertEqual(self.section.subjects.count(), 3)
        self.assertFalse(Subject.all_objects.get(id=first.id).is_deleted)

        self.client.post(reverse("topics:redo_subject_action", args=[self.section.id]))
        self.assertEqual(list(self.section.subjects.values_list("id", flat=True)), [third.id])

    def test_undo_bulk_add_and_new_action_clears_redo(self):
        add_url = reverse("topics:bulk_add_subjects", args=[self.section.id])
        self.client.post(
            add_url,
            {
                "source_entries": "One\nTwo",
                "entries": "One\nTwo",
                "common_subtitle": "",
                "color": "default",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )
        self.assertEqual(self.section.subjects.count(), 2)

        self.client.post(reverse("topics:undo_subject_action", args=[self.section.id]))
        self.assertEqual(self.section.subjects.count(), 0)

        self.client.post(
            reverse("topics:add_subject", args=[self.section.id]),
            {
                "title": "Replacement",
                "description": "",
                "color": "default",
                "weekly_goal_minutes": 120,
                "priority": "normal",
            },
        )
        section_page = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )
        self.assertFalse(section_page.context["can_redo_subject_action"])
        self.assertEqual(
            list(self.section.subjects.values_list("title", flat=True)),
            ["Replacement"],
        )

    def test_section_page_has_selection_and_history_controls(self):
        Subject.objects.create(section=self.section, title="Selectable")
        response = self.client.get(
            reverse("topics:section_detail", args=[self.section.id])
        )

        self.assertContains(response, "Select cards")
        self.assertContains(response, "Delete selected")
        self.assertContains(response, "Undo")
        self.assertContains(response, "Redo")
        self.assertContains(response, "subject_bulk_actions.js")

    def test_bulk_add_rejects_another_users_section(self):
        other_user = get_user_model().objects.create_user(
            username="other-bulk-user",
            password="test-pass-123",
        )
        other_topic = Topic.objects.create(user=other_user, title="Private")
        other_section = Section.objects.create(topic=other_topic, title="Private section")

        response = self.client.get(
            reverse("topics:bulk_add_subjects", args=[other_section.id])
        )

        self.assertEqual(response.status_code, 404)
