from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from zoneinfo import ZoneInfo

from topics.models import Section, Subject, Topic
from users.models import UserPreferences

from .models import Milestone, Task


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

    def test_completed_task_moves_to_journal_with_optional_reflection(self):
        task = Task.objects.create(
            user=self.user,
            title="Finish the portfolio project",
            priority="high",
        )

        response = self.client.post(
            reverse("planner:toggle_task", args=[task.id]),
            {"completion_note": "Finished the API and understood the test flow."},
        )

        self.assertRedirects(response, reverse("topics:home"))
        task.refresh_from_db()
        self.assertTrue(task.completed)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(
            task.completion_note,
            "Finished the API and understood the test flow.",
        )

        dashboard = self.client.get(reverse("topics:home"))
        self.assertNotContains(dashboard, "Finish the portfolio project")

        completed_date = timezone.localdate(task.completed_at)
        journal = self.client.get(
            reverse("planner:task_journal"),
            {"date": completed_date.isoformat()},
        )
        self.assertContains(journal, "Finish the portfolio project")
        self.assertContains(journal, "Finished the API and understood the test flow.")
        self.assertContains(journal, "Edit reflection")

    def test_task_can_be_completed_without_a_reflection(self):
        task = Task.objects.create(user=self.user, title="Clean the room")

        self.client.post(reverse("planner:toggle_task", args=[task.id]))

        task.refresh_from_db()
        self.assertTrue(task.completed)
        self.assertEqual(task.completion_note, "")
        journal = self.client.get(
            reverse("planner:task_journal"),
            {"date": timezone.localdate(task.completed_at).isoformat()},
        )
        self.assertContains(journal, "No reflection added yet.")
        self.assertContains(journal, "Add reflection")

    def test_journal_reflection_can_be_edited_and_task_restored(self):
        task = Task.objects.create(
            user=self.user,
            title="Practise violin",
            completed=True,
            completed_at=timezone.now(),
        )
        completed_date = timezone.localdate(task.completed_at)
        return_data = {
            "return_to": "journal",
            "journal_date": completed_date.isoformat(),
        }

        reflection_response = self.client.post(
            reverse("planner:update_task_reflection", args=[task.id]),
            {**return_data, "completion_note": "Learned the difficult middle section."},
        )
        self.assertRedirects(
            reflection_response,
            f'{reverse("planner:task_journal")}?date={completed_date.isoformat()}',
        )
        task.refresh_from_db()
        self.assertEqual(task.completion_note, "Learned the difficult middle section.")

        restore_response = self.client.post(
            reverse("planner:toggle_task", args=[task.id]),
            return_data,
        )
        self.assertRedirects(
            restore_response,
            f'{reverse("planner:task_journal")}?date={completed_date.isoformat()}',
        )
        task.refresh_from_db()
        self.assertFalse(task.completed)
        self.assertIsNone(task.completed_at)
        self.assertEqual(task.completion_note, "Learned the difficult middle section.")

        dashboard = self.client.get(reverse("topics:home"))
        self.assertContains(dashboard, "Practise violin")

    def test_user_cannot_edit_another_users_journal_reflection(self):
        task = Task.objects.create(
            user=self.other,
            title="Private result",
            completed=True,
            completed_at=timezone.now(),
        )

        response = self.client.post(
            reverse("planner:update_task_reflection", args=[task.id]),
            {"completion_note": "Changed"},
        )

        self.assertEqual(response.status_code, 404)
        task.refresh_from_db()
        self.assertEqual(task.completion_note, "")

    def test_existing_task_can_be_edited_without_recreating_it(self):
        task = Task.objects.create(
            user=self.user,
            title="Prepare application",
            priority="normal",
        )
        due_date = timezone.localdate() + timedelta(days=3)

        response = self.client.post(
            reverse("planner:edit_task", args=[task.id]),
            {
                "task_type": "regular",
                "title": "Prepare university application",
                "due_date": due_date.isoformat(),
                "priority": "high",
            },
        )

        self.assertRedirects(response, reverse("topics:home"))
        task.refresh_from_db()
        self.assertEqual(task.title, "Prepare university application")
        self.assertEqual(task.due_date, due_date)
        self.assertEqual(task.priority, "high")
        self.assertEqual(Task.objects.filter(user=self.user).count(), 1)

    def test_pinned_tasks_and_priority_control_dashboard_order(self):
        normal = Task.objects.create(
            user=self.user,
            title="Normal task",
            priority="normal",
        )
        high = Task.objects.create(
            user=self.user,
            title="High task",
            priority="high",
        )
        pinned_low = Task.objects.create(
            user=self.user,
            title="Pinned low task",
            priority="low",
        )

        pin_response = self.client.post(
            reverse("planner:toggle_task_pin", args=[pinned_low.id])
        )
        self.assertRedirects(pin_response, reverse("topics:home"))
        pinned_low.refresh_from_db()
        self.assertTrue(pinned_low.is_pinned)

        dashboard = self.client.get(reverse("topics:home"))
        tasks = list(dashboard.context["tasks"])
        self.assertEqual(tasks[:3], [pinned_low, high, normal])
        self.assertContains(dashboard, f'data-task-edit-url="{reverse("planner:edit_task", args=[normal.id])}"')
        self.assertContains(dashboard, "Pinned")

    def test_user_cannot_edit_or_pin_another_users_task(self):
        task = Task.objects.create(user=self.other, title="Private")

        edit_response = self.client.post(
            reverse("planner:edit_task", args=[task.id]),
            {
                "task_type": "regular",
                "title": "Changed",
                "priority": "high",
            },
        )
        pin_response = self.client.post(
            reverse("planner:toggle_task_pin", args=[task.id])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(pin_response.status_code, 404)
        task.refresh_from_db()
        self.assertEqual(task.title, "Private")
        self.assertFalse(task.is_pinned)

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

    def test_deadline_uses_the_users_local_date_and_appears_on_dashboard(self):
        preferences, _ = UserPreferences.objects.get_or_create(user=self.user)
        preferences.timezone = "Asia/Qyzylorda"
        preferences.save(update_fields=["timezone"])

        response = self.client.post(reverse("planner:add_milestone"), {
            "kind": "deadline",
            "title": "Submit portfolio project",
            "target_at": "2026-08-10T18:30",
            "priority": "high",
        })

        self.assertRedirects(response, reverse("topics:home"))
        milestone = Milestone.objects.get(user=self.user)
        local_target = milestone.target_at.astimezone(ZoneInfo("Asia/Qyzylorda"))
        self.assertEqual(local_target.strftime("%Y-%m-%dT%H:%M"), "2026-08-10T18:30")
        self.assertEqual(milestone.kind, "deadline")
        self.assertEqual(milestone.priority, "high")

        dashboard = self.client.get(reverse("topics:home"))
        self.assertContains(dashboard, "Plans &amp; deadlines")
        self.assertContains(dashboard, "Submit portfolio project")
        self.assertContains(dashboard, "Aug 10, 2026")
        self.assertContains(dashboard, "18:30")

    def test_deadline_requires_a_date_but_plan_can_stay_flexible(self):
        deadline_response = self.client.post(reverse("planner:add_milestone"), {
            "kind": "deadline",
            "title": "Prepare for IMAT",
            "target_at": "",
            "priority": "normal",
        })
        self.assertRedirects(deadline_response, reverse("topics:home"))
        self.assertFalse(Milestone.objects.filter(user=self.user).exists())

        plan_response = self.client.post(reverse("planner:add_milestone"), {
            "kind": "plan",
            "title": "Prepare for IMAT",
            "target_at": "",
            "priority": "normal",
        })
        self.assertRedirects(plan_response, reverse("topics:home"))
        milestone = Milestone.objects.get(user=self.user)
        self.assertIsNone(milestone.target_at)

    def test_milestone_can_be_completed_and_its_importance_changed(self):
        milestone = Milestone.objects.create(
            user=self.user,
            kind="plan",
            title="Build a new project",
            priority="low",
        )

        priority_response = self.client.post(
            reverse("planner:update_milestone_priority", args=[milestone.id]),
            {"priority": "high"},
        )
        self.assertRedirects(priority_response, reverse("topics:home"))
        milestone.refresh_from_db()
        self.assertEqual(milestone.priority, "high")

        toggle_response = self.client.post(
            reverse("planner:toggle_milestone", args=[milestone.id])
        )
        self.assertRedirects(toggle_response, reverse("topics:home"))
        milestone.refresh_from_db()
        self.assertTrue(milestone.completed)
        self.assertIsNotNone(milestone.completed_at)

    def test_user_cannot_change_or_delete_another_users_milestone(self):
        milestone = Milestone.objects.create(
            user=self.other,
            kind="plan",
            title="Private plan",
        )

        self.assertEqual(
            self.client.post(
                reverse("planner:toggle_milestone", args=[milestone.id])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("planner:update_milestone_priority", args=[milestone.id]),
                {"priority": "high"},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("planner:delete_milestone", args=[milestone.id])
            ).status_code,
            404,
        )
        self.assertTrue(Milestone.objects.filter(id=milestone.id).exists())

    def test_full_plans_page_keeps_long_details_and_completed_history(self):
        active = Milestone.objects.create(
            user=self.user,
            kind="plan",
            title="Prepare the university application",
            description="Collect documents.\nWrite the motivation letter.\nAsk for feedback.",
            priority="high",
        )
        completed = Milestone.objects.create(
            user=self.user,
            kind="deadline",
            title="Submit the first portfolio version",
            description="Uploaded the finished project and demo.",
            target_at=timezone.now() - timedelta(days=1),
            completed=True,
            completed_at=timezone.now(),
        )

        response = self.client.get(reverse("planner:milestone_hub"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, active.title)
        self.assertContains(response, "Collect documents.")
        self.assertContains(response, completed.title)
        self.assertContains(response, "Completed history")
        self.assertContains(response, 'class="learning-breadcrumb-link"')
        self.assertContains(response, 'class="learning-breadcrumb-current"')

    def test_plan_can_be_created_and_edited_from_full_page(self):
        create_response = self.client.post(
            reverse("planner:add_milestone"),
            {
                "return_to": "milestones",
                "kind": "plan",
                "title": "Learn a violin piece",
                "description": "Practise the difficult middle section slowly.",
                "target_at": "",
                "priority": "normal",
            },
        )
        self.assertRedirects(create_response, reverse("planner:milestone_hub"))
        milestone = Milestone.objects.get(user=self.user)
        self.assertEqual(
            milestone.description,
            "Practise the difficult middle section slowly.",
        )

        update_response = self.client.post(
            reverse("planner:update_milestone", args=[milestone.id]),
            {
                "return_to": "milestones",
                "kind": "plan",
                "title": "Learn the complete violin piece",
                "description": "Now practise it from beginning to end.",
                "target_at": "",
                "priority": "high",
            },
        )
        self.assertRedirects(update_response, reverse("planner:milestone_hub"))
        milestone.refresh_from_db()
        self.assertEqual(milestone.title, "Learn the complete violin piece")
        self.assertEqual(milestone.priority, "high")

    def test_dashboard_only_previews_five_active_plans(self):
        for index in range(7):
            Milestone.objects.create(
                user=self.user,
                title=f"Plan {index}",
                priority="normal",
            )
        Milestone.objects.create(
            user=self.user,
            title="Already completed",
            completed=True,
            completed_at=timezone.now(),
        )

        response = self.client.get(reverse("topics:home"))

        self.assertEqual(len(response.context["milestones"]), 5)
        self.assertEqual(response.context["milestone_more_count"], 2)
        self.assertNotContains(response, "Already completed")
        self.assertContains(response, "View 2 more plans")
        self.assertContains(response, 'data-milestone-list-size="compact"')
        self.assertContains(response, 'data-milestone-size-change="-1"')
        self.assertContains(response, 'data-milestone-size-change="1"')

    def test_user_cannot_edit_another_users_milestone(self):
        milestone = Milestone.objects.create(
            user=self.other,
            kind="plan",
            title="Private plan",
        )

        response = self.client.post(
            reverse("planner:update_milestone", args=[milestone.id]),
            {
                "return_to": "milestones",
                "kind": "plan",
                "title": "Changed",
                "description": "Changed",
                "target_at": "",
                "priority": "high",
            },
        )

        self.assertEqual(response.status_code, 404)
        milestone.refresh_from_db()
        self.assertEqual(milestone.title, "Private plan")
