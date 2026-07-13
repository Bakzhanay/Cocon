from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from topics.models import Section, Subject, Topic

from .models import Flashcard


class FlashcardSecurityAndReviewTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="owner", password="test-pass-123")
        self.other = users.objects.create_user(username="other", password="test-pass-123")
        topic = Topic.objects.create(user=self.user, title="Biology")
        section = Section.objects.create(topic=topic, title="Cells")
        self.subject = Subject.objects.create(section=section, title="Mitosis")
        self.card = Flashcard.objects.create(subject=self.subject, question="Q", answer="A")
        self.client.force_login(self.other)

    def test_another_user_cannot_edit_delete_or_toggle_card(self):
        self.assertEqual(self.client.get(reverse("flashcards:edit_flashcard", args=[self.card.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("flashcards:delete_flashcard", args=[self.card.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("flashcards:toggle_flashcard", args=[self.card.id])).status_code, 404)

    def test_good_review_schedules_owned_card(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("flashcards:review_flashcard", args=[self.card.id]),
            {"rating": "good"},
        )
        self.assertEqual(response.status_code, 302)
        self.card.refresh_from_db()
        self.assertTrue(self.card.learned)
        self.assertEqual(self.card.interval_days, 1)
        self.assertIsNotNone(self.card.next_review_at)

    def test_due_page_lists_owned_due_cards(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("flashcards:due_flashcards"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reviews due")
        self.assertContains(response, self.card.question)
        self.assertContains(response, "Biology / Cells / Mitosis")
