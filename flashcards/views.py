import random
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from topics.models import Section, Subject

from .forms import BulkFlashcardForm, FlashcardForm
from .models import Flashcard


def owned_flashcards(user):
    return Flashcard.objects.filter(
        Q(section__topic__user=user)
        | Q(
            subject__is_deleted=False,
            subject__section__topic__user=user,
        )
    ).distinct()


def split_cards(cards):
    active = []
    learned = []
    for card in cards:
        if card.learned:
            learned.append(card)
        else:
            active.append(card)
    return active, learned


def ordered_active_cards(cards, preferred_order=None, *, now=None, shuffle=False):
    """Put due cards first and keep future reviews in date-based buckets.

    A saved shuffle order is treated as a preference inside each review bucket,
    never as permission to put a card scheduled for later above a due card.
    """
    now = now or timezone.now()
    cards = list(cards)
    by_id = {card.id: card for card in cards}

    preferred_ids = set(preferred_order or [])
    if preferred_order:
        ordered = [by_id[card_id] for card_id in preferred_order if card_id in by_id]
        ordered.extend(card for card in cards if card.id not in preferred_ids)
    else:
        ordered = cards

    due_cards = [
        card
        for card in ordered
        if card.next_review_at is None or card.next_review_at <= now
    ]
    future_cards = [
        card
        for card in ordered
        if card.next_review_at is not None and card.next_review_at > now
    ]

    if not preferred_order:
        due_cards.sort(
            key=lambda card: (
                card.next_review_at is not None,
                card.next_review_at or now,
                card.created_at,
                card.id,
            )
        )

    future_buckets = {}
    for card in future_cards:
        # Group by the user's local calendar day, not the UTC date stored by
        # Django, so a late-evening review is not shown under the wrong day.
        review_date = timezone.localtime(card.next_review_at).date()
        future_buckets.setdefault(review_date, []).append(card)

    if shuffle:
        _shuffle_bucket(due_cards)
        for bucket in future_buckets.values():
            _shuffle_bucket(bucket)
    else:
        for bucket in future_buckets.values():
            if not preferred_order:
                bucket.sort(key=lambda card: (card.next_review_at, card.created_at, card.id))

    ordered_future = [
        card
        for review_date in sorted(future_buckets)
        for card in future_buckets[review_date]
    ]
    return due_cards + ordered_future


def _shuffle_bucket(cards):
    if len(cards) <= 1:
        return
    original = cards.copy()
    random.shuffle(cards)
    if cards == original:
        cards[:] = original[1:] + original[:1]


def card_progress(active_cards, learned_cards):
    total = len(active_cards) + len(learned_cards)
    learned_count = len(learned_cards)
    percent = int((learned_count / total) * 100) if total else 0
    return total, learned_count, percent


def card_redirect(card):
    if card.section_id:
        return redirect("flashcards:section_flashcards", section_id=card.section_id)
    return redirect("flashcards:subject_flashcards", subject_id=card.subject_id)


def _bulk_flashcard_page(request, *, subject=None, section=None):
    context_object = subject or section
    if request.method == "POST":
        form = BulkFlashcardForm(request.POST)
        if form.is_valid():
            existing_pairs = {
                (question.strip().casefold(), answer.strip().casefold())
                for question, answer in context_object.flashcards.values_list(
                    "question", "answer"
                )
            }
            pending_cards = []
            batch_pairs = set()
            for entry in form.cleaned_data["parsed_entries"]:
                pair = (
                    entry["question"].strip().casefold(),
                    entry["answer"].strip().casefold(),
                )
                if pair in existing_pairs or pair in batch_pairs:
                    continue
                batch_pairs.add(pair)
                pending_cards.append(Flashcard(
                    subject=subject,
                    section=section,
                    question=entry["question"],
                    answer=entry["answer"],
                    notes=entry["notes"],
                ))

            if pending_cards:
                with transaction.atomic():
                    Flashcard.objects.bulk_create(pending_cards)
            skipped = len(form.cleaned_data["parsed_entries"]) - len(pending_cards)
            if pending_cards:
                message = f"Added {len(pending_cards)} flashcard"
                if len(pending_cards) != 1:
                    message += "s"
                if skipped:
                    message += f"; skipped {skipped} exact duplicate"
                    if skipped != 1:
                        message += "s"
                messages.success(request, message + ".")
            else:
                messages.info(request, "No cards were added because all were exact duplicates.")

            if subject:
                return redirect("flashcards:subject_flashcards", subject_id=subject.id)
            return redirect("flashcards:section_flashcards", section_id=section.id)
    else:
        form = BulkFlashcardForm()

    return render(request, "flashcards/bulk_add_flashcards.html", {
        "form": form,
        "subject": subject,
        "section": section,
        "title": context_object.title,
        "current_activity_type": "flashcards",
    })


@login_required
def due_flashcards(request):
    now = timezone.now()
    cards = (
        owned_flashcards(request.user)
        .filter(
            Q(next_review_at__lte=now)
            | Q(next_review_at__isnull=True, learned=False)
        )
        .select_related(
            "section__topic",
            "subject__section__topic",
        )
        .order_by("next_review_at", "created_at")
    )
    return render(request, "flashcards/due_flashcards.html", {
        "due_cards": cards,
        "due_count": cards.count(),
        "due_review_page": True,
        "current_activity_type": "flashcards",
    })


@login_required
def section_flashcards(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    active_cards, learned_cards = split_cards(
        section.flashcards.order_by("created_at", "id")
    )
    active_cards = ordered_active_cards(active_cards)
    total, learned_count, progress_percent = card_progress(active_cards, learned_cards)
    return render(request, "flashcards/section_flashcards.html", {
        "section": section,
        "active_cards": active_cards,
        "learned_cards": learned_cards,
        "total_count": total,
        "learned_count": learned_count,
        "progress_percent": progress_percent,
        "current_activity_type": "flashcards",
    })


@login_required
def add_section_flashcard(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    if request.method == "POST":
        form = FlashcardForm(request.POST, request.FILES)
        if form.is_valid():
            card = form.save(commit=False)
            card.section = section
            card.save()
            return redirect("flashcards:section_flashcards", section_id=section.id)
    else:
        form = FlashcardForm()
    return render(request, "flashcards/add_flashcard.html", {
        "form": form,
        "title": section.title,
        "section": section,
        "current_activity_type": "flashcards",
    })


@login_required
def bulk_add_section_flashcards(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    return _bulk_flashcard_page(request, section=section)


@login_required
def edit_flashcard(request, flashcard_id):
    flashcard = get_object_or_404(owned_flashcards(request.user), id=flashcard_id)
    if request.method == "POST":
        form = FlashcardForm(request.POST, request.FILES, instance=flashcard)
        if form.is_valid():
            form.save()
            return card_redirect(flashcard)
    else:
        form = FlashcardForm(instance=flashcard)
    return render(request, "flashcards/edit_flashcard.html", {
        "form": form,
        "flashcard": flashcard,
        "subject": flashcard.subject,
        "section": flashcard.section,
        "current_activity_type": "flashcards",
    })


@login_required
def delete_flashcard(request, flashcard_id):
    flashcard = get_object_or_404(owned_flashcards(request.user), id=flashcard_id)
    if request.method == "POST":
        destination = (
            ("flashcards:section_flashcards", {"section_id": flashcard.section_id})
            if flashcard.section_id
            else ("flashcards:subject_flashcards", {"subject_id": flashcard.subject_id})
        )
        flashcard.delete()
        return redirect(destination[0], **destination[1])
    return render(request, "flashcards/delete_flashcard.html", {
        "flashcard": flashcard,
        "subject": flashcard.subject,
        "section": flashcard.section,
        "current_activity_type": "flashcards",
    })


@login_required
def subject_flashcards(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    active_cards, learned_cards = split_cards(
        subject.flashcards.order_by("created_at", "id")
    )
    order = request.session.get(f"flashcard_order_{subject.id}")
    active_cards = ordered_active_cards(active_cards, preferred_order=order)
    total, learned_count, progress_percent = card_progress(active_cards, learned_cards)
    return render(request, "flashcards/subject_flashcards.html", {
        "subject": subject,
        "active_cards": active_cards,
        "learned_cards": learned_cards,
        "total_count": total,
        "learned_count": learned_count,
        "progress_percent": progress_percent,
        "current_activity_type": "flashcards",
    })


@login_required
def add_subject_flashcard(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    if request.method == "POST":
        form = FlashcardForm(request.POST, request.FILES)
        if form.is_valid():
            card = form.save(commit=False)
            card.subject = subject
            card.save()
            return redirect("flashcards:subject_flashcards", subject_id=subject.id)
    else:
        form = FlashcardForm()
    return render(request, "flashcards/add_flashcard.html", {
        "form": form,
        "title": subject.title,
        "subject": subject,
        "current_activity_type": "flashcards",
    })


@login_required
def bulk_add_subject_flashcards(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        is_deleted=False,
        section__topic__user=request.user,
    )
    return _bulk_flashcard_page(request, subject=subject)


@login_required
def delete_question_image(request, flashcard_id):
    flashcard = get_object_or_404(owned_flashcards(request.user), id=flashcard_id)
    if request.method == "POST" and flashcard.question_image:
        flashcard.question_image.delete(save=False)
        flashcard.question_image = None
        flashcard.save(update_fields=["question_image"])
        return redirect("flashcards:edit_flashcard", flashcard_id=flashcard.id)
    return render(request, "flashcards/delete_question_image.html", {
        "flashcard": flashcard,
        "subject": flashcard.subject,
        "section": flashcard.section,
    })


@login_required
def toggle_flashcard(request, flashcard_id):
    flashcard = get_object_or_404(owned_flashcards(request.user), id=flashcard_id)
    flashcard.learned = not flashcard.learned
    if flashcard.learned:
        # Mastery is a manual, user-controlled state.  Once a card is marked
        # mastered it should not keep displaying an old review date.
        flashcard.next_review_at = None
        flashcard.review_state = ""
    else:
        flashcard.next_review_at = None
        flashcard.repetitions = 0
        flashcard.interval_days = 0
        flashcard.review_state = ""
    flashcard.save(update_fields=[
        "learned",
        "next_review_at",
        "repetitions",
        "interval_days",
        "review_state",
    ])
    if request.GET.get("return_to") == "due":
        return redirect("flashcards:due_flashcards")
    return card_redirect(flashcard)


@login_required
@require_POST
def review_flashcard(request, flashcard_id):
    flashcard = get_object_or_404(owned_flashcards(request.user), id=flashcard_id)
    rating = request.POST.get("rating")
    if rating not in {"again", "hard", "good", "easy"}:
        return card_redirect(flashcard)

    now = timezone.now()
    ease = Decimal(flashcard.ease_factor)
    if rating == "again":
        flashcard.repetitions = 0
        flashcard.interval_days = 0
        flashcard.ease_factor = max(Decimal("1.30"), ease - Decimal("0.20"))
        # Again means “show this card in the current learning pass again”,
        # rather than scheduling a separate 10-minute review.
        flashcard.next_review_at = now
    elif rating == "hard":
        flashcard.repetitions += 1
        flashcard.ease_factor = max(Decimal("1.30"), ease - Decimal("0.15"))
        if flashcard.interval_days:
            flashcard.interval_days = max(1, round(flashcard.interval_days * 1.2))
            flashcard.next_review_at = now + timedelta(days=flashcard.interval_days)
        else:
            # A new or reset card gets one short relearning step before it
            # enters the daily queue.  This makes Hard meaningfully earlier
            # than Good without showing the card again immediately.
            flashcard.next_review_at = now + timedelta(minutes=10)
    elif rating == "good":
        flashcard.repetitions += 1
        if not flashcard.interval_days:
            flashcard.interval_days = 1
        elif flashcard.interval_days == 1 and flashcard.repetitions <= 2:
            flashcard.interval_days = 3
        else:
            flashcard.interval_days = max(1, round((flashcard.interval_days or 1) * float(ease)))
        flashcard.next_review_at = now + timedelta(days=flashcard.interval_days)
    else:
        flashcard.repetitions += 1
        flashcard.ease_factor = min(Decimal("3.50"), ease + Decimal("0.15"))
        flashcard.interval_days = 3 if not flashcard.interval_days else max(
            1,
            round(flashcard.interval_days * float(flashcard.ease_factor) * 1.3),
        )
        flashcard.next_review_at = now + timedelta(days=flashcard.interval_days)

    flashcard.last_reviewed_at = now
    flashcard.review_state = rating
    flashcard.save(update_fields=[
        "repetitions",
        "interval_days",
        "ease_factor",
        "next_review_at",
        "last_reviewed_at",
        "review_state",
    ])
    if request.POST.get("return_to_due") == "1":
        return redirect("flashcards:due_flashcards")
    return card_redirect(flashcard)


@login_required
def shuffle_subject_flashcards(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    active_cards = list(
        subject.flashcards
        .filter(learned=False)
        .order_by("created_at", "id")
    )
    shuffled_cards = ordered_active_cards(active_cards, shuffle=True)
    ids = [card.id for card in shuffled_cards]
    session_key = f"flashcard_order_{subject.id}"
    request.session[session_key] = ids
    return redirect("flashcards:subject_flashcards", subject_id=subject_id)


@login_required
def restore_subject_flashcards(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    request.session.pop(f"flashcard_order_{subject.id}", None)
    return redirect("flashcards:subject_flashcards", subject_id=subject.id)
