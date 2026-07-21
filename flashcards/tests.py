from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

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

    def test_good_review_schedules_owned_card_without_mastering_it(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("flashcards:review_flashcard", args=[self.card.id]),
            {"rating": "good"},
        )
        self.assertEqual(response.status_code, 302)
        self.card.refresh_from_db()
        self.assertFalse(self.card.learned)
        self.assertEqual(self.card.interval_days, 1)
        self.assertIsNotNone(self.card.next_review_at)

    def test_review_ratings_do_not_change_manual_mastery_state(self):
        self.client.force_login(self.user)

        for learned in (False, True):
            for rating in ("again", "hard", "good", "easy"):
                with self.subTest(learned=learned, rating=rating):
                    card = Flashcard.objects.create(
                        subject=self.subject,
                        question=f"{rating}-{learned}",
                        answer="A",
                        learned=learned,
                    )
                    self.client.post(
                        reverse("flashcards:review_flashcard", args=[card.id]),
                        {"rating": rating},
                    )
                    card.refresh_from_db()
                    self.assertEqual(card.learned, learned)

    def test_due_page_lists_owned_due_cards(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("flashcards:due_flashcards"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reviews due")
        self.assertContains(response, self.card.question)
        self.assertContains(response, "Biology / Cells / Mitosis")

    def test_again_review_keeps_card_in_active_deck(self):
        self.client.force_login(self.user)

        self.client.post(
            reverse("flashcards:review_flashcard", args=[self.card.id]),
            {"rating": "again"},
        )
        response = self.client.get(
            reverse("flashcards:subject_flashcards", args=[self.subject.id])
        )

        self.card.refresh_from_db()
        self.assertFalse(self.card.learned)
        self.assertIsNotNone(self.card.next_review_at)
        self.assertIn(self.card, response.context["active_cards"])
        self.assertNotIn(self.card, response.context["learned_cards"])

    def test_mastered_card_moves_to_bottom_and_is_not_shuffled(self):
        self.client.force_login(self.user)
        second = Flashcard.objects.create(
            subject=self.subject,
            question="Second",
            answer="A2",
        )
        mastered = Flashcard.objects.create(
            subject=self.subject,
            question="Mastered",
            answer="A3",
            learned=True,
        )

        with patch("flashcards.views.random.shuffle", side_effect=lambda values: values.reverse()):
            self.client.get(
                reverse("flashcards:shuffle_subject_flashcards", args=[self.subject.id])
            )

        session_order = self.client.session[f"flashcard_order_{self.subject.id}"]
        self.assertEqual(session_order, [second.id, self.card.id])
        self.assertNotIn(mastered.id, session_order)

        response = self.client.get(
            reverse("flashcards:subject_flashcards", args=[self.subject.id])
        )
        self.assertEqual(
            [card.id for card in response.context["active_cards"]],
            [second.id, self.card.id],
        )
        self.assertEqual(
            [card.id for card in response.context["learned_cards"]],
            [mastered.id],
        )

    def test_shuffle_changes_order_when_random_returns_same_order(self):
        self.client.force_login(self.user)
        second = Flashcard.objects.create(
            subject=self.subject,
            question="Second",
            answer="A2",
        )

        with patch("flashcards.views.random.shuffle", return_value=None):
            self.client.get(
                reverse("flashcards:shuffle_subject_flashcards", args=[self.subject.id])
            )

        self.assertEqual(
            self.client.session[f"flashcard_order_{self.subject.id}"],
            [second.id, self.card.id],
        )
