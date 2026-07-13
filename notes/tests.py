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
