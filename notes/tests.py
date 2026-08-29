from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from topics.models import Section, Subject, Topic

from .models import Note, QuickNote


class DashboardNoteTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="notes-owner", password="test-pass-123")
        topic = Topic.objects.create(user=self.user, title="Science")
        section = Section.objects.create(topic=topic, title="Biology")
        self.subject = Subject.objects.create(section=section, title="Cells")
        self.note = Note.objects.create(owner=self.user, subject=self.subject, title="Important", content="Remember this")
        self.client.force_login(self.user)

    def test_note_can_be_pinned_to_dashboard(self):
        response = self.client.post(reverse("notes:toggle_pin", args=[self.note.id]))
        self.assertEqual(response.status_code, 302)
        self.note.refresh_from_db()
        self.assertTrue(self.note.is_pinned)
        self.assertContains(self.client.get(reverse("topics:home")), "Important")

    def test_pinned_subject_note_is_rendered_before_newer_unpinned_note(self):
        newer_note = Note.objects.create(
            owner=self.user,
            subject=self.subject,
            title="Newer unpinned note",
            content="This note was created later",
        )

        response = self.client.post(
            reverse("notes:toggle_pin", args=[self.note.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        notes = list(response.context["notes"])
        self.assertEqual(notes[0], self.note)
        self.assertEqual(notes[1], newer_note)
        self.assertLess(
            response.content.index(b"Important"),
            response.content.index(b"Newer unpinned note"),
        )

    def test_unpinned_subject_note_returns_to_recency_order(self):
        newer_note = Note.objects.create(
            owner=self.user,
            subject=self.subject,
            title="Newer unpinned note",
            content="This note was created later",
        )
        self.note.is_pinned = True
        self.note.save(update_fields=["is_pinned"])

        response = self.client.post(
            reverse("notes:toggle_pin", args=[self.note.id]),
            follow=True,
        )

        notes = list(response.context["notes"])
        self.assertEqual(notes[0], newer_note)
        self.assertEqual(notes[1], self.note)

    def test_section_note_list_places_pinned_notes_first(self):
        section = self.subject.section
        older_pinned_note = Note.objects.create(
            owner=self.user,
            section=section,
            title="Pinned section note",
            content="Keep this first",
            is_pinned=True,
        )
        newer_note = Note.objects.create(
            owner=self.user,
            section=section,
            title="Newer section note",
            content="Created later",
        )

        response = self.client.get(reverse("topics:section_detail", args=[section.id]))

        notes = list(response.context["notes"])
        self.assertEqual(notes[0], older_pinned_note)
        self.assertEqual(notes[1], newer_note)

    def test_quick_note_can_be_added(self):
        response = self.client.post(reverse("notes:add_quick_note"), {"content": "Call the tutor"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(QuickNote.objects.filter(owner=self.user, content="Call the tutor").exists())

    def test_quick_note_page_can_pin_note(self):
        quick_note = QuickNote.objects.create(owner=self.user, content="Remember the application deadline")

        response = self.client.post(reverse("notes:toggle_quick_note_pin", args=[quick_note.id]))

        self.assertRedirects(response, reverse("notes:quick_notes"))
        quick_note.refresh_from_db()
        self.assertTrue(quick_note.is_pinned)
        page = self.client.get(reverse("notes:quick_notes"))
        self.assertContains(page, "Remember the application deadline")
        self.assertContains(page, "Unpin")

    def test_deleted_quick_note_can_be_undone_without_losing_its_content_or_pin(self):
        quick_note = QuickNote.objects.create(
            owner=self.user,
            content="Do not lose this thought",
            is_pinned=True,
        )

        delete_response = self.client.post(
            reverse("notes:delete_quick_note", args=[quick_note.id])
        )

        self.assertRedirects(
            delete_response,
            f'{reverse("notes:quick_notes")}?quick_note_deleted={quick_note.id}',
        )
        quick_note.refresh_from_db()
        self.assertIsNotNone(quick_note.deleted_at)

        deleted_page = self.client.get(delete_response.url)
        self.assertNotContains(deleted_page, "Do not lose this thought")
        self.assertContains(deleted_page, "Quick note deleted")
        self.assertContains(deleted_page, "Undo")

        undo_response = self.client.post(
            reverse("notes:undo_delete_quick_note", args=[quick_note.id])
        )
        self.assertRedirects(undo_response, reverse("notes:quick_notes"))
        quick_note.refresh_from_db()
        self.assertIsNone(quick_note.deleted_at)
        self.assertTrue(quick_note.is_pinned)
        self.assertContains(
            self.client.get(reverse("notes:quick_notes")),
            "Do not lose this thought",
        )

    def test_user_cannot_undo_another_users_deleted_quick_note(self):
        user_model = get_user_model()
        other = user_model.objects.create_user(
            username="other-notes-owner",
            password="test-pass-123",
        )
        quick_note = QuickNote.objects.create(
            owner=other,
            content="Private deleted thought",
        )
        quick_note.deleted_at = quick_note.updated_at
        quick_note.save(update_fields=["deleted_at"])

        response = self.client.post(
            reverse("notes:undo_delete_quick_note", args=[quick_note.id])
        )

        self.assertEqual(response.status_code, 404)
        quick_note.refresh_from_db()
        self.assertIsNotNone(quick_note.deleted_at)
