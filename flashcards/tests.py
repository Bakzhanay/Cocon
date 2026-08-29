from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from django import forms
from topics.models import Section, Subject, Topic

from .forms import BulkFlashcardForm, parse_bulk_flashcards
from .models import Flashcard


class FlashcardSecurityAndReviewTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="owner", password="test-pass-123")
        self.other = users.objects.create_user(username="other", password="test-pass-123")
        topic = Topic.objects.create(user=self.user, title="Biology")
        self.section = Section.objects.create(topic=topic, title="Cells")
        self.subject = Subject.objects.create(section=self.section, title="Mitosis")
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

    def test_new_card_ratings_have_distinct_learning_steps(self):
        self.client.force_login(self.user)

        expected_minutes = {"hard": 10}
        for rating, minutes in expected_minutes.items():
            with self.subTest(rating=rating):
                card = Flashcard.objects.create(
                    subject=self.subject,
                    question=f"{rating} question",
                    answer="A",
                )
                before = timezone.now()
                self.client.post(
                    reverse("flashcards:review_flashcard", args=[card.id]),
                    {"rating": rating},
                )
                card.refresh_from_db()
                self.assertEqual(card.interval_days, 0)
                self.assertGreaterEqual(
                    card.next_review_at,
                    before + timedelta(minutes=minutes - 1),
                )
                self.assertLessEqual(
                    card.next_review_at,
                    timezone.now() + timedelta(minutes=minutes + 1),
                )

        again_card = Flashcard.objects.create(
            subject=self.subject,
            question="again question",
            answer="A",
        )
        before = timezone.now()
        self.client.post(
            reverse("flashcards:review_flashcard", args=[again_card.id]),
            {"rating": "again"},
        )
        again_card.refresh_from_db()
        self.assertEqual(again_card.interval_days, 0)
        self.assertGreaterEqual(again_card.next_review_at, before)
        self.assertLessEqual(again_card.next_review_at, timezone.now())
        self.assertEqual(again_card.review_state, "again")

        for rating, days in (("good", 1), ("easy", 3)):
            with self.subTest(rating=rating):
                card = Flashcard.objects.create(
                    subject=self.subject,
                    question=f"{rating} question",
                    answer="A",
                )
                before = timezone.now()
                self.client.post(
                    reverse("flashcards:review_flashcard", args=[card.id]),
                    {"rating": rating},
                )
                card.refresh_from_db()
                self.assertEqual(card.interval_days, days)
                self.assertGreaterEqual(
                    card.next_review_at,
                    before + timedelta(days=days) - timedelta(seconds=1),
                )

    def test_rating_labels_reflect_next_intervals(self):
        self.assertEqual(self.card.hard_interval_label, "10m")
        self.assertEqual(self.card.good_interval_label, "1d+")
        self.assertEqual(self.card.easy_interval_label, "3d+")

        self.card.interval_days = 1
        self.card.repetitions = 2
        self.card.save(update_fields=["interval_days", "repetitions"])
        self.assertEqual(self.card.hard_interval_label, "1d+")
        self.assertEqual(self.card.good_interval_label, "3d+")
        self.assertIn("d+", self.card.easy_interval_label)

    def test_review_schedule_hides_stale_dates_for_mastered_cards(self):
        self.card.learned = True
        self.card.next_review_at = timezone.now() - timedelta(days=4)
        self.card.review_state = "easy"
        self.card.save(update_fields=["learned", "next_review_at", "review_state"])

        self.assertEqual(self.card.review_schedule_label, "")

        self.card.learned = False
        self.card.next_review_at = timezone.now() - timedelta(days=4)
        self.card.save(update_fields=["learned", "next_review_at"])
        self.assertEqual(self.card.review_schedule_label, "Review due")

    def test_mastery_toggle_clears_review_schedule_and_learning_state(self):
        self.client.force_login(self.user)
        self.card.review_state = "hard"
        self.card.next_review_at = timezone.now() - timedelta(days=2)
        self.card.save(update_fields=["review_state", "next_review_at"])

        self.client.get(reverse("flashcards:toggle_flashcard", args=[self.card.id]))
        self.card.refresh_from_db()
        self.assertTrue(self.card.learned)
        self.assertIsNone(self.card.next_review_at)
        self.assertEqual(self.card.review_state, "")

        self.client.get(reverse("flashcards:toggle_flashcard", args=[self.card.id]))
        self.card.refresh_from_db()
        self.assertFalse(self.card.learned)
        self.assertIsNone(self.card.next_review_at)
        self.assertEqual(self.card.review_state, "")

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

    def test_subject_flashcards_show_the_full_breadcrumb_path(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("flashcards:subject_flashcards", args=[self.subject.id])
        )

        self.assertContains(response, 'aria-label="Learning path"')
        self.assertContains(
            response,
            (
                f'href="{reverse("topics:topic_detail", args=[self.subject.section.topic_id])}" '
                'class="learning-breadcrumb-link"'
            ),
        )
        self.assertContains(
            response,
            (
                f'href="{reverse("topics:section_detail", args=[self.subject.section_id])}" '
                'class="learning-breadcrumb-link"'
            ),
        )
        self.assertContains(
            response,
            (
                f'href="{reverse("topics:subject_overview", args=[self.subject.id])}" '
                'class="learning-breadcrumb-link"'
            ),
        )
        self.assertContains(
            response,
            '<span class="learning-breadcrumb-current" aria-current="page">Flashcards</span>',
            html=True,
        )

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

    def test_due_cards_stay_above_future_cards(self):
        self.client.force_login(self.user)
        future = Flashcard.objects.create(
            subject=self.subject,
            question="Future",
            answer="A2",
            next_review_at=timezone.now() + timedelta(days=1),
            interval_days=1,
            repetitions=1,
        )
        due = Flashcard.objects.create(
            subject=self.subject,
            question="Due",
            answer="A3",
            next_review_at=timezone.now() - timedelta(minutes=1),
            interval_days=1,
            repetitions=1,
        )

        with patch("flashcards.views.random.shuffle", side_effect=lambda values: values.reverse()):
            self.client.get(
                reverse("flashcards:shuffle_subject_flashcards", args=[self.subject.id])
            )

        response = self.client.get(
            reverse("flashcards:subject_flashcards", args=[self.subject.id])
        )
        active_ids = [card.id for card in response.context["active_cards"]]
        self.assertLess(active_ids.index(due.id), active_ids.index(future.id))

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


class BulkFlashcardTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(
            username="deck-owner",
            password="test-pass-123",
        )
        self.other = users.objects.create_user(
            username="deck-other",
            password="test-pass-123",
        )
        self.topic = Topic.objects.create(user=self.user, title="Biology")
        self.section = Section.objects.create(topic=self.topic, title="Cells")
        self.subject = Subject.objects.create(section=self.section, title="Cell membrane")
        self.client.force_login(self.user)

    def test_parser_preserves_multiline_question_answer_and_notes(self):
        cards = parse_bulk_flashcards(
            "Question: Explain the fluid mosaic model.\n"
            "Include the role of phospholipids.\n"
            "Answer: The membrane is a fluid phospholipid bilayer.\n\n"
            "Proteins move within it and perform transport and signalling.\n"
            "Notes: Compare integral and peripheral proteins.\n"
            "This note has a second line.\n"
            "---\n"
            "Question: What is osmosis?\n"
            "Answer: The net movement of water down its water-potential gradient."
        )

        self.assertEqual(len(cards), 2)
        self.assertIn("Include the role", cards[0]["question"])
        self.assertIn("\n\nProteins move", cards[0]["answer"])
        self.assertIn("second line", cards[0]["notes"])

    def test_parser_requires_both_question_and_answer(self):
        with self.assertRaises(forms.ValidationError):
            parse_bulk_flashcards("Question: An unanswered question")

    def test_subject_bulk_add_saves_long_text_notes_and_order(self):
        long_answer = "A detailed explanation. " * 500
        response = self.client.post(
            reverse("flashcards:bulk_add_subject_flashcards", args=[self.subject.id]),
            {
                "source_entries": (
                    f"Question: First question\nAnswer: {long_answer}\n"
                    "Notes: First private study note\n---\n"
                    "Question: Second question\nAnswer: Second answer"
                ),
                "preview_ready": "0",
                "entries": "",
            },
        )

        self.assertRedirects(
            response,
            reverse("flashcards:subject_flashcards", args=[self.subject.id]),
        )
        cards = list(self.subject.flashcards.order_by("created_at", "id"))
        self.assertEqual([card.question for card in cards], ["First question", "Second question"])
        self.assertEqual(cards[0].answer, long_answer.strip())
        self.assertEqual(cards[0].notes, "First private study note")

    def test_preview_json_is_authoritative_and_duplicate_pairs_are_skipped(self):
        Flashcard.objects.create(
            subject=self.subject,
            question="Existing",
            answer="Answer",
        )
        entries = (
            '[{"question":"Existing","answer":"Answer","notes":"different"},'
            '{"question":"New edited question","answer":"New edited answer","notes":"note"},'
            '{"question":"new edited question","answer":"new edited answer","notes":"again"}]'
        )
        response = self.client.post(
            reverse("flashcards:bulk_add_subject_flashcards", args=[self.subject.id]),
            {
                "source_entries": "Question: ignored\nAnswer: ignored",
                "preview_ready": "1",
                "entries": entries,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.subject.flashcards.count(), 2)
        self.assertTrue(
            self.subject.flashcards.filter(
                question="New edited question",
                notes="note",
            ).exists()
        )

    def test_section_bulk_add_creates_section_cards(self):
        response = self.client.post(
            reverse("flashcards:bulk_add_section_flashcards", args=[self.section.id]),
            {
                "source_entries": "Question: Section question\nAnswer: Section answer",
                "preview_ready": "0",
                "entries": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        card = self.section.flashcards.get(question="Section question")
        self.assertIsNone(card.subject_id)

    def test_subject_deck_links_to_bulk_add_page(self):
        response = self.client.get(
            reverse("flashcards:subject_flashcards", args=[self.subject.id])
        )

        self.assertContains(
            response,
            reverse("flashcards:bulk_add_subject_flashcards", args=[self.subject.id]),
        )
        self.assertContains(response, "Bulk add")

    def test_bulk_add_page_includes_ai_format_and_editable_preview(self):
        response = self.client.get(
            reverse("flashcards:bulk_add_subject_flashcards", args=[self.subject.id])
        )

        self.assertContains(response, "Copy AI prompt")
        self.assertContains(response, "Question: What is photosynthesis?")
        self.assertContains(response, "bulkFlashcardPreviewList")
        self.assertContains(response, "js/bulk_flashcard_editor.js")

    def test_bulk_add_rejects_another_users_subject_and_section(self):
        other_topic = Topic.objects.create(user=self.other, title="Private")
        other_section = Section.objects.create(topic=other_topic, title="Private section")
        other_subject = Subject.objects.create(section=other_section, title="Private subject")

        self.assertEqual(
            self.client.get(
                reverse("flashcards:bulk_add_subject_flashcards", args=[other_subject.id])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("flashcards:bulk_add_section_flashcards", args=[other_section.id])
            ).status_code,
            404,
        )

    def test_bulk_form_limits_batch_count_not_text_length(self):
        too_many = "\n---\n".join(
            f"Question: Q{index}\nAnswer: A{index}" for index in range(201)
        )
        form = BulkFlashcardForm(data={
            "source_entries": too_many,
            "preview_ready": "0",
            "entries": "",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("up to 200", str(form.errors))
