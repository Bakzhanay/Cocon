import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from topics.models import Section, Subject, Topic
from planner.models import Task

from .analytics import aggregate_sessions
from .models import StudySession, StudySessionSegment


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
        start_payload = start_response.json()
        session_id = start_payload["session_id"]
        self.assertEqual(start_payload["context"], {
            "topic_id": self.topic.id,
            "section_id": self.section.id,
            "subject_id": self.subject.id,
            "activity_type": "general",
            "label": "Biology / Cells / Mitosis",
        })

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

    def test_activity_calendar_includes_completed_to_do_journal_entries(self):
        completed_at = timezone.now()
        task = Task.objects.create(
            user=self.user,
            title="Review the lesson",
            completed=True,
            completed_at=completed_at,
            completion_note="Understood the main idea.",
        )
        local_date = timezone.localdate(task.completed_at)

        activity_response = self.client.get(
            reverse("study:activity"),
            {"year": local_date.year, "month": local_date.month},
        )

        self.assertEqual(activity_response.status_code, 200)
        self.assertEqual(
            activity_response.json()["completed_tasks"],
            [{"date": local_date.isoformat(), "count": 1}],
        )

    def test_navigation_splits_focus_between_section_notes_and_flashcards(self):
        start_response = self.post_json("study:start_session", {
            "topic_id": self.topic.id,
            "section_id": self.section.id,
            "activity_type": "general",
        })
        session_id = start_response.json()["session_id"]

        notes_context = self.post_json("study:sync_session_context", {
            "session_id": session_id,
            "elapsed_seconds": 300,
            "subject_id": self.subject.id,
            "activity_type": "notes",
        })
        self.assertEqual(notes_context.status_code, 200)
        self.assertTrue(notes_context.json()["changed"])
        self.assertEqual(
            notes_context.json()["context"]["label"],
            "Biology / Cells / Mitosis / Notes",
        )

        flashcards_context = self.post_json("study:sync_session_context", {
            "session_id": session_id,
            "elapsed_seconds": 900,
            "subject_id": self.subject.id,
            "activity_type": "flashcards",
        })
        self.assertEqual(flashcards_context.status_code, 200)

        self.post_json("study:stop_session", {
            "session_id": session_id,
            "duration_seconds": 1500,
        })

        segments = list(
            StudySessionSegment.objects
            .filter(session_id=session_id)
            .order_by("id")
        )
        self.assertEqual(
            [segment.duration_seconds for segment in segments],
            [300, 600, 600],
        )
        self.assertIsNone(segments[0].subject)
        self.assertEqual(segments[1].subject, self.subject)
        self.assertEqual(segments[1].activity_type, "notes")
        self.assertEqual(segments[2].activity_type, "flashcards")

        snapshot = aggregate_sessions(
            StudySession.objects.filter(id=session_id, completed=True)
        )
        self.assertEqual(snapshot["total_seconds"], 1500)
        self.assertEqual(snapshot["session_count"], 1)
        self.assertEqual(snapshot["totals"]["topic"][self.topic.id], 1500)
        self.assertEqual(snapshot["totals"]["section"][self.section.id], 1500)
        self.assertEqual(snapshot["totals"]["subject"][self.subject.id], 1200)
        self.assertEqual(
            snapshot["activities"]["subject"][(self.subject.id, "notes")],
            600,
        )
        self.assertEqual(
            snapshot["activities"]["subject"][(self.subject.id, "flashcards")],
            600,
        )

    def test_context_sync_rejects_another_users_subject(self):
        other_topic = Topic.objects.create(user=self.other_user, title="Private")
        other_section = Section.objects.create(topic=other_topic, title="Private section")
        other_subject = Subject.objects.create(section=other_section, title="Private subject")
        session_id = self.post_json("study:start_session", {
            "section_id": self.section.id,
        }).json()["session_id"]

        response = self.post_json("study:sync_session_context", {
            "session_id": session_id,
            "elapsed_seconds": 300,
            "subject_id": other_subject.id,
            "activity_type": "notes",
        })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            StudySessionSegment.objects.filter(session_id=session_id).count(),
            1,
        )

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
        self.assertContains(response, 'id="trackingContextLock"')
        self.assertContains(response, "Follow the page I open")

    def test_completed_sessions_automatically_fill_and_complete_study_plan(self):
        task = Task.objects.create(
            user=self.user,
            title="Study cells",
            section=self.section,
            target_minutes=25,
            due_date=timezone.localdate(),
        )

        first_start = self.post_json("study:start_session", {
            "subject_id": self.subject.id,
            "activity_type": "notes",
        }).json()
        self.assertEqual(first_start["task"]["id"], task.id)
        first_stop = self.post_json("study:stop_session", {
            "session_id": first_start["session_id"],
            "duration_seconds": 600,
        }).json()
        self.assertEqual(first_stop["task"]["focused_minutes"], 10)
        self.assertFalse(first_stop["task"]["completed"])

        second_start = self.post_json("study:start_session", {
            "subject_id": self.subject.id,
            "activity_type": "flashcards",
        }).json()
        second_stop = self.post_json("study:stop_session", {
            "session_id": second_start["session_id"],
            "duration_seconds": 900,
        }).json()

        task.refresh_from_db()
        self.assertEqual(task.focused_seconds, 1500)
        self.assertTrue(task.completed)
        self.assertTrue(task.completed_by_focus)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(second_stop["task"]["progress_percent"], 100)

        completed_date = timezone.localdate(task.completed_at)
        journal = self.client.get(
            reverse("planner:task_journal"),
            {"date": completed_date.isoformat()},
        )
        self.assertContains(journal, "Study cells")
        self.assertContains(journal, "Completed by focus time")
        self.assertContains(journal, "No reflection added yet.")

        repeated_stop = self.post_json("study:stop_session", {
            "session_id": second_start["session_id"],
            "duration_seconds": 900,
        })
        self.assertTrue(repeated_stop.json()["already_completed"])
        task.refresh_from_db()
        self.assertEqual(task.focused_seconds, 1500)

    def test_most_specific_matching_plan_receives_the_session(self):
        topic_task = Task.objects.create(
            user=self.user,
            title="Study biology",
            topic=self.topic,
            target_minutes=60,
            due_date=timezone.localdate(),
        )
        subject_task = Task.objects.create(
            user=self.user,
            title="Study mitosis",
            subject=self.subject,
            target_minutes=30,
            due_date=timezone.localdate(),
        )

        start = self.post_json("study:start_session", {
            "subject_id": self.subject.id,
        }).json()
        self.assertEqual(start["task"]["id"], subject_task.id)
        self.post_json("study:stop_session", {
            "session_id": start["session_id"],
            "duration_seconds": 900,
        })

        topic_task.refresh_from_db()
        subject_task.refresh_from_db()
        self.assertEqual(topic_task.focused_seconds, 0)
        self.assertEqual(subject_task.focused_seconds, 900)

    def test_starting_from_task_uses_its_context_and_rejects_another_users_task(self):
        task = Task.objects.create(
            user=self.user,
            title="Review mitosis",
            subject=self.subject,
            activity_type="flashcards",
            target_minutes=25,
            due_date=timezone.localdate() + timedelta(days=1),
        )
        start_response = self.post_json("study:start_session", {"task_id": task.id})
        self.assertEqual(start_response.status_code, 200)
        session = StudySession.objects.get(id=start_response.json()["session_id"])
        self.assertEqual(session.task, task)
        self.assertEqual(session.subject, self.subject)
        self.assertEqual(session.activity_type, "flashcards")

        other_task = Task.objects.create(
            user=self.other_user,
            title="Private plan",
            target_minutes=25,
        )
        response = self.post_json("study:start_session", {"task_id": other_task.id})
        self.assertEqual(response.status_code, 404)

    def test_focus_history_lists_only_the_signed_in_users_sessions(self):
        own_session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            section=self.section,
            subject=self.subject,
            started_at=timezone.now() - timedelta(minutes=25),
            ended_at=timezone.now(),
            duration_seconds=1500,
            completed=True,
            status="completed",
        )
        StudySession.objects.create(
            user=self.other_user,
            topic_title="Private topic",
            started_at=timezone.now() - timedelta(minutes=10),
            ended_at=timezone.now(),
            duration_seconds=600,
            completed=True,
            status="completed",
        )

        response = self.client.get(reverse("study:session_history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_session.context_label)
        self.assertContains(response, "25 min")
        self.assertNotContains(response, "Private topic")

    def test_clearing_dashboard_activity_never_deletes_history_or_statistics(self):
        old_session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            started_at=timezone.now() - timedelta(minutes=10),
            ended_at=timezone.now() - timedelta(seconds=1),
            duration_seconds=600,
            completed=True,
            status="completed",
        )

        clear_response = self.client.post(reverse("study:clear_dashboard_activity"))
        self.assertRedirects(clear_response, reverse("topics:home"))

        dashboard = self.client.get(reverse("topics:home"))
        self.assertEqual(list(dashboard.context["recent_sessions"]), [])
        self.assertEqual(dashboard.context["week_minutes"], 10)
        self.assertTrue(dashboard.context["has_focus_history"])
        self.assertTrue(StudySession.objects.filter(id=old_session.id).exists())

        history = self.client.get(reverse("study:session_history"))
        self.assertContains(history, old_session.context_label)

        preferences = self.user.study_preferences
        new_session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            started_at=preferences.dashboard_activity_hidden_before + timedelta(seconds=1),
            ended_at=preferences.dashboard_activity_hidden_before + timedelta(seconds=2),
            duration_seconds=300,
            completed=True,
            status="completed",
        )
        dashboard = self.client.get(reverse("topics:home"))
        self.assertEqual(list(dashboard.context["recent_sessions"]), [new_session])
