import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from topics.models import Section, Subject

from .forms import FlashcardForm
from .models import Flashcard


def owned_flashcards(user):
    return Flashcard.objects.filter(
        Q(section__topic__user=user)
        | Q(subject__section__topic__user=user)
    ).distinct()


def split_cards(cards):
    now = timezone.now()
    active = []
    learned = []
    for card in cards:
        is_due = card.next_review_at and card.next_review_at <= now
        is_new = not card.learned and card.next_review_at is None
        if is_new or is_due:
            active.append(card)
        else:
            learned.append(card)
    return active, learned


def card_progress(active_cards, learned_cards):
    total = len(active_cards) + len(learned_cards)
    learned_count = len(learned_cards)
    percent = int((learned_count / total) * 100) if total else 0
    return total, learned_count, percent


def card_redirect(card):
    if card.section_id:
        return redirect("flashcards:section_flashcards", section_id=card.section_id)
    return redirect("flashcards:subject_flashcards", subject_id=card.subject_id)


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
    active_cards, learned_cards = split_cards(section.flashcards.all())
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
    active_cards, learned_cards = split_cards(subject.flashcards.all())
    order = request.session.get(f"flashcard_order_{subject.id}")
    if order:
        by_id = {card.id: card for card in active_cards}
        active_cards = [by_id.pop(card_id) for card_id in order if card_id in by_id]
        active_cards.extend(by_id.values())
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
    if not flashcard.learned:
        flashcard.next_review_at = None
        flashcard.repetitions = 0
        flashcard.interval_days = 0
    flashcard.save(update_fields=["learned", "next_review_at", "repetitions", "interval_days"])
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
        flashcard.next_review_at = now + timedelta(minutes=10)
        flashcard.learned = False
    elif rating == "hard":
        flashcard.repetitions += 1
        flashcard.interval_days = max(1, round((flashcard.interval_days or 1) * 1.2))
        flashcard.ease_factor = max(Decimal("1.30"), ease - Decimal("0.15"))
        flashcard.next_review_at = now + timedelta(days=flashcard.interval_days)
        flashcard.learned = False
    elif rating == "good":
        flashcard.repetitions += 1
        if flashcard.repetitions == 1:
            flashcard.interval_days = 1
        elif flashcard.repetitions == 2:
            flashcard.interval_days = 3
        else:
            flashcard.interval_days = max(1, round((flashcard.interval_days or 1) * float(ease)))
        flashcard.next_review_at = now + timedelta(days=flashcard.interval_days)
        flashcard.learned = True
    else:
        flashcard.repetitions += 1
        flashcard.ease_factor = min(Decimal("3.50"), ease + Decimal("0.15"))
        flashcard.interval_days = 4 if not flashcard.interval_days else max(
            1,
            round(flashcard.interval_days * float(flashcard.ease_factor) * 1.3),
        )
        flashcard.next_review_at = now + timedelta(days=flashcard.interval_days)
        flashcard.learned = True

    flashcard.last_reviewed_at = now
    flashcard.save(update_fields=[
        "repetitions",
        "interval_days",
        "ease_factor",
        "next_review_at",
        "last_reviewed_at",
        "learned",
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
    ids = list(subject.flashcards.filter(learned=False).values_list("id", flat=True))
    random.shuffle(ids)
    request.session[f"flashcard_order_{subject.id}"] = ids
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
