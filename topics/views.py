from django.utils import timezone
from django.db.models import Sum
from study.models import StudySession, StudySessionSegment
from study.analytics import aggregate_sessions, build_focus_analytics, format_duration
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import (
    Topic,
    Section,
    Subject,
    SubjectHistoryAction,
    SubjectSubtitlePreset,
)
from .forms import TopicForm, SectionForm, SubjectForm, BulkSubjectForm

from flashcards.models import Flashcard
from notes.models import Note, QuickNote
from planner.models import Milestone, Task
from users.models import UserPreferences

from django.db.models import Q


DASHBOARD_WIDGETS = ("tasks", "milestones", "quick_notes", "pinned_notes")
RHYTHM_PERIODS = {
    "7d": {
        "label": "Last 7 days",
        "aria_label": "Focus minutes for the last seven days",
    },
    "30d": {
        "label": "Last 30 days",
        "aria_label": "Focus minutes for the last thirty days",
    },
    "year": {
        "label": "Last 12 months",
        "aria_label": "Focus minutes for the last twelve months",
    },
}
RHYTHM_ACTIVITY_LABELS = {
    "general": "General study",
    "notes": "Notes",
    "flashcards": "Flashcards",
    "reading": "Reading",
}


def _dashboard_widget_preferences(preferences, field_name):
    """Return a clean, predictable list even if saved JSON was edited manually."""
    saved_widgets = getattr(preferences, field_name, [])
    if not isinstance(saved_widgets, list):
        return []
    return [widget for widget in DASHBOARD_WIDGETS if widget in saved_widgets]


def _shift_month(month_start, offset):
    """Return the first day of the month ``offset`` months away."""
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return month_start.replace(year=year, month=zero_based_month + 1, day=1)


def _build_focus_rhythm(completed_sessions, user_timezone, today, period):
    """Build dashboard chart buckets without changing stored session data."""
    if period not in RHYTHM_PERIODS:
        period = "7d"

    if period == "year":
        current_month = today.replace(day=1)
        bucket_dates = [_shift_month(current_month, offset) for offset in range(-11, 1)]
        period_start = bucket_dates[0]
        labels = [month.strftime("%b") for month in bucket_dates]
        bucket_key = lambda local_day: local_day.replace(day=1)
    else:
        day_count = 30 if period == "30d" else 7
        period_start = today - timedelta(days=day_count - 1)
        bucket_dates = [period_start + timedelta(days=offset) for offset in range(day_count)]
        labels = [
            day.strftime("%d") if period == "30d" else day.strftime("%a")
            for day in bucket_dates
        ]
        bucket_key = lambda local_day: local_day

    period_start_at = datetime.combine(period_start, time.min, tzinfo=user_timezone)
    tomorrow_start = datetime.combine(today + timedelta(days=1), time.min, tzinfo=user_timezone)
    period_sessions = completed_sessions.filter(
        ended_at__gte=period_start_at,
        ended_at__lt=tomorrow_start,
    )
    totals = {}
    for ended_at, duration in period_sessions.values_list("ended_at", "duration_seconds"):
        local_day = ended_at.astimezone(user_timezone).date()
        key = bucket_key(local_day)
        totals[key] = totals.get(key, 0) + duration

    breakdown_totals = {}

    def add_breakdown_row(
        ended_at,
        seconds,
        topic_title,
        section_title,
        subject_title,
        activity_type,
    ):
        if not ended_at or not seconds:
            return
        local_day = ended_at.astimezone(user_timezone).date()
        key = bucket_key(local_day)
        area_label = topic_title or "General study"
        activity_label = RHYTHM_ACTIVITY_LABELS.get(activity_type, "General study")
        if subject_title:
            context_label = f"{subject_title} / {activity_label}"
        elif section_title:
            context_label = f"{section_title} / {activity_label}"
        elif topic_title:
            context_label = f"Topic-level / {activity_label}"
        else:
            context_label = activity_label

        area = breakdown_totals.setdefault(key, {}).setdefault(
            area_label,
            {"seconds": 0, "contexts": {}},
        )
        area["seconds"] += seconds
        area["contexts"][context_label] = (
            area["contexts"].get(context_label, 0) + seconds
        )

    segment_rows = list(
        StudySessionSegment.objects.filter(session__in=period_sessions).values(
            "session_id",
            "session__ended_at",
            "duration_seconds",
            "topic__title",
            "topic_title",
            "section__title",
            "section_title",
            "subject__title",
            "subject_title",
            "activity_type",
        )
    )
    segmented_session_ids = {row["session_id"] for row in segment_rows}
    for row in segment_rows:
        add_breakdown_row(
            row["session__ended_at"],
            row["duration_seconds"],
            row["topic__title"] or row["topic_title"],
            row["section__title"] or row["section_title"],
            row["subject__title"] or row["subject_title"],
            row["activity_type"],
        )

    legacy_rows = period_sessions.exclude(id__in=segmented_session_ids).values(
        "ended_at",
        "duration_seconds",
        "topic__title",
        "topic_title",
        "section__title",
        "section_title",
        "subject__title",
        "subject_title",
        "activity_type",
    )
    for row in legacy_rows:
        add_breakdown_row(
            row["ended_at"],
            row["duration_seconds"],
            row["topic__title"] or row["topic_title"],
            row["section__title"] or row["section_title"],
            row["subject__title"] or row["subject_title"],
            row["activity_type"],
        )

    max_bucket_seconds = max([*totals.values(), 1])
    chart = []
    for bucket_date, label in zip(bucket_dates, labels):
        seconds = totals.get(bucket_date, 0)
        breakdown = []
        for area_label, area in sorted(
            breakdown_totals.get(bucket_date, {}).items(),
            key=lambda item: (-item[1]["seconds"], item[0].lower()),
        ):
            contexts = [
                {
                    "label": context_label,
                    "seconds": context_seconds,
                    "duration": format_duration(context_seconds),
                }
                for context_label, context_seconds in sorted(
                    area["contexts"].items(),
                    key=lambda item: (-item[1], item[0].lower()),
                )
            ]
            breakdown.append({
                "label": area_label,
                "seconds": area["seconds"],
                "duration": format_duration(area["seconds"]),
                "contexts": contexts,
            })
        chart.append({
            "date": bucket_date,
            "label": label,
            "minutes": round(seconds / 60),
            "height": max(4, round((seconds / max_bucket_seconds) * 100)) if seconds else 4,
            "display_date": (
                bucket_date.strftime("%B %Y")
                if period == "year"
                else bucket_date.strftime("%B %d, %Y").replace(" 0", " ")
            ),
            "breakdown": breakdown,
            "is_current": (
                bucket_date == today.replace(day=1)
                if period == "year"
                else bucket_date == today
            ),
        })

    return {
        "period": period,
        "label": RHYTHM_PERIODS[period]["label"],
        "aria_label": RHYTHM_PERIODS[period]["aria_label"],
        "chart": chart,
        "total_minutes": round(sum(totals.values()) / 60),
    }


def _study_session_resume_url(session):
    """Return the most specific study page that still exists for a session."""
    if not session:
        return None

    if session.subject:
        if session.activity_type == "flashcards":
            route_name = "flashcards:subject_flashcards"
        elif session.activity_type == "notes":
            route_name = "topics:subject_detail"
        else:
            route_name = "topics:subject_overview"
        path = reverse(route_name, args=[session.subject_id])
    elif session.section:
        path = reverse("topics:section_detail", args=[session.section_id])
    elif session.topic:
        path = reverse("topics:topic_detail", args=[session.topic_id])
    else:
        return None

    return f"{path}?focus=resume"


def _focus_snapshot(user):
    """Return all completed Pomodoro time grouped by learning context."""
    sessions = StudySession.objects.filter(
        user=user,
        completed=True,
        status="completed",
    )
    return aggregate_sessions(sessions)


def _user_timezone(user):
    preferences, _ = UserPreferences.objects.get_or_create(user=user)
    try:
        return ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _manual_focus_duration(request):
    try:
        hours = int(request.POST.get("hours") or 0)
        minutes = int(request.POST.get("minutes") or 0)
    except (TypeError, ValueError) as error:
        raise ValueError("Enter time using whole hours and minutes.") from error

    total_minutes = hours * 60 + minutes
    if (
        hours < 0
        or minutes < 0
        or minutes > 59
        or not 1 <= total_minutes <= 24 * 60
    ):
        raise ValueError(
            "Enter between 1 minute and 24 hours. Minutes must be from 0 to 59."
        )
    return total_minutes * 60


def _manual_focus_ended_at(request):
    user_timezone = _user_timezone(request.user)
    now = timezone.now().astimezone(user_timezone)
    raw_date = (request.POST.get("focus_date") or "").strip()
    if not raw_date:
        selected_date = now.date()
    else:
        try:
            selected_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError as error:
            raise ValueError("Choose a valid date.") from error
    if selected_date > now.date():
        raise ValueError("Manual focus time cannot be added in the future.")
    return datetime.combine(
        selected_date,
        now.time().replace(tzinfo=None),
        tzinfo=user_timezone,
    )


def _manual_focus_redirect(subject):
    return (
        f"{reverse('topics:subject_overview', args=[subject.id])}"
        "?manage_time=1#manual-focus-time"
    )


def _add_focus_to_sections(sections, snapshot):
    for section in sections:
        seconds = snapshot["totals"]["section"].get(section.id, 0)
        section.focus_seconds = seconds
        section.focus_duration = format_duration(seconds)


def _add_focus_to_subjects(subjects, snapshot):
    activity_totals = snapshot["activities"]["subject"]
    for subject in subjects:
        total_seconds = snapshot["totals"]["subject"].get(subject.id, 0)
        notes_seconds = activity_totals.get((subject.id, "notes"), 0)
        flashcards_seconds = activity_totals.get((subject.id, "flashcards"), 0)
        subject_study_seconds = max(
            0,
            total_seconds - notes_seconds - flashcards_seconds,
        )

        subject.focus_seconds = total_seconds
        subject.focus_duration = format_duration(total_seconds)
        subject.notes_focus_seconds = notes_seconds
        subject.notes_focus_duration = format_duration(notes_seconds)
        subject.flashcards_focus_seconds = flashcards_seconds
        subject.flashcards_focus_duration = format_duration(flashcards_seconds)
        subject.subject_study_seconds = subject_study_seconds
        subject.subject_study_duration = format_duration(subject_study_seconds)


def _subject_subtitle_history(section, limit=20):
    return list(
        section.subtitle_presets.values_list("value", flat=True)[:limit]
    )


def _remember_subject_subtitles(section, values):
    now = timezone.now()
    unique_values = []
    seen = set()
    for raw_value in values:
        value = (raw_value or "").strip()
        normalized = value.casefold()
        if not value or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(value)

    for value in unique_values:
        existing = section.subtitle_presets.filter(value__iexact=value).first()
        if existing:
            SubjectSubtitlePreset.objects.filter(pk=existing.pk).update(
                last_used_at=now
            )
        else:
            SubjectSubtitlePreset.objects.create(section=section, value=value)


def _record_subject_action(user, section, action_type, subject_ids):
    """Add an undoable subject action and discard an abandoned redo branch."""
    subject_ids = [subject_id for subject_id in subject_ids if subject_id]
    if not subject_ids:
        return None

    section.subject_history_actions.filter(user=user, is_undone=True).delete()
    action = SubjectHistoryAction.objects.create(
        user=user,
        section=section,
        action_type=action_type,
        subject_ids=subject_ids,
    )
    old_action_ids = list(
        section.subject_history_actions.filter(user=user)
        .order_by("-created_at", "-id")
        .values_list("id", flat=True)[50:]
    )
    if old_action_ids:
        SubjectHistoryAction.objects.filter(id__in=old_action_ids).delete()
    return action


def _set_subjects_deleted(section, subject_ids, deleted):
    return Subject.all_objects.filter(
        section=section,
        id__in=subject_ids,
    ).update(
        is_deleted=deleted,
        deleted_at=timezone.now() if deleted else None,
    )

# Create your views here.
@login_required
def home(request):

    topics = Topic.objects.filter(
    user=request.user
    ).order_by("title")

    return render(
        request,
        "topics/home.html",
        {
            "topics": topics
        }
    )


@login_required
def add_topic(request):

    if request.method == "POST":
        form = TopicForm(request.POST)

        if form.is_valid():

            topic = form.save(commit=False)
            topic.user = request.user
            topic.save()

            return redirect("topics:home")

    else:
        form = TopicForm()

    return render(
        request,
        "topics/add_topic.html",
        {
            "form": form
        }
    )

@login_required
def edit_topic(request, topic_id):
    topic = get_object_or_404(
        Topic,
        id=topic_id,
        user=request.user
    )

    if request.method == "POST":
        form = TopicForm(request.POST, instance=topic)

        if form.is_valid():
            form.save()
            return redirect("topics:home")

    else:
        form = TopicForm(instance=topic)

    return render(
        request,
        "topics/edit_topic.html",
        {"form": form, "topic": topic},
    )

@login_required
def delete_topic(request, topic_id):
    topic = get_object_or_404(
        Topic,
        id=topic_id,
        user=request.user,
    )

    if request.method == "POST":
        topic.delete()
        return redirect("topics:home")

    return render(
        request,
        "topics/delete_topic.html",
        {"topic": topic},
    )


@login_required
@require_POST
def toggle_topic_pin(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, user=request.user)
    topic.is_pinned = not topic.is_pinned
    topic.save(update_fields=["is_pinned"])

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("topics:home")


@login_required
@require_POST
def toggle_section_pin(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    section.is_pinned = not section.is_pinned
    section.save(update_fields=["is_pinned"])

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("topics:topic_detail", topic_id=section.topic_id)


@login_required
@require_POST
def toggle_subject_pin(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    subject.is_pinned = not subject.is_pinned
    subject.save(update_fields=["is_pinned"])

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("topics:section_detail", section_id=subject.section_id)


@login_required
def topic_detail(request, topic_id):

    topic = get_object_or_404(
        Topic,
        id=topic_id,
        user=request.user,
    )

    sections = list(
        topic.sections
        .annotate(
            subject_count=Count(
                "subjects",
                filter=Q(subjects__is_deleted=False),
            )
        )
        .order_by("-is_pinned", "title")
    )
    focus_snapshot = _focus_snapshot(request.user)
    _add_focus_to_sections(sections, focus_snapshot)
    topic.focus_seconds = focus_snapshot["totals"]["topic"].get(topic.id, 0)
    topic.focus_duration = format_duration(topic.focus_seconds)

    return render(
        request,
        "topics/topic_detail.html",
        {
            "topic": topic,
            "sections": sections,
            "current_topic": topic.id,
        },
    )

@login_required
def add_section(request, topic_id):

    topic = get_object_or_404(
        Topic,
        id=topic_id,
        user=request.user,
    )

    if request.method == "POST":

        form = SectionForm(request.POST)

        if form.is_valid():

            section = form.save(commit=False)
            section.topic = topic
            section.save()

            return redirect(
                "topics:topic_detail",
                topic_id=topic.id,
            )

    else:

        form = SectionForm()

    return render(
        request,
        "topics/add_section.html",
        {
            "form": form,
            "topic": topic,
        },
    )

@login_required
def edit_section(request, section_id):

    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    if request.method == "POST":

        form = SectionForm(
            request.POST,
            instance=section,
        )

        if form.is_valid():

            form.save()

            return redirect(
                "topics:topic_detail",
                topic_id=section.topic.id,
            )

    else:

        form = SectionForm(instance=section)

    return render(
        request,
        "topics/edit_section.html",
        {
            "form": form,
            "section": section,
        },
    )

@login_required
def delete_section(request, section_id):

    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    if request.method == "POST":

        topic_id = section.topic.id
        section.delete()

        return redirect(
            "topics:topic_detail",
            topic_id=topic_id,
        )

    return render(
        request,
        "topics/delete_section.html",
        {
            "section": section,
        },
    )

@login_required
def section_detail(request, section_id):

    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    subjects = list(section.subjects.all())
    total_subjects = len(subjects)
    completed_subjects = sum(subject.completed for subject in subjects)
    focus_snapshot = _focus_snapshot(request.user)
    _add_focus_to_subjects(subjects, focus_snapshot)
    section.focus_seconds = focus_snapshot["totals"]["section"].get(section.id, 0)
    section.focus_duration = format_duration(section.focus_seconds)
    return render(
        request,
        "topics/section_detail.html",
        {
            "section": section,
            "subjects": subjects,
            "total_subjects": total_subjects,
            "completed_subjects": completed_subjects,
            "subjects_progress": round((completed_subjects / total_subjects) * 100) if total_subjects else 0,
            "subject_color_choices": Subject.COLOR_CHOICES,
            "notes": section.notes.all().order_by("-is_pinned", "-updated_at", "-id"),
            "current_topic": section.topic.id,
            "current_section": section.id,
            "can_undo_subject_action": section.subject_history_actions.filter(
                user=request.user,
                is_undone=False,
            ).exists(),
            "can_redo_subject_action": section.subject_history_actions.filter(
                user=request.user,
                is_undone=True,
            ).exists(),
        },
    )

@login_required
def add_subject(request, section_id):

    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    if request.method == "POST":

        form = SubjectForm(request.POST)

        if form.is_valid():

            subject = form.save(commit=False)
            subject.section = section
            subject.save()
            _remember_subject_subtitles(section, [subject.description])
            _record_subject_action(request.user, section, "create", [subject.id])

            return redirect(
                "topics:section_detail",
                section_id=section.id,
            )

    else:

        form = SubjectForm()

    return render(
        request,
        "topics/add_subject.html",
        {
            "form": form,
            "section": section,
            "subtitle_history": _subject_subtitle_history(section),
        },
    )


@login_required
def bulk_add_subjects(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    if request.method == "POST":
        form = BulkSubjectForm(request.POST)
        if form.is_valid():
            existing_titles = {
                title.casefold()
                for title in section.subjects.values_list("title", flat=True)
            }
            pending_subjects = []
            subtitles = []
            skipped = 0

            for entry in form.cleaned_data["parsed_entries"]:
                normalized_title = entry["title"].casefold()
                if normalized_title in existing_titles:
                    skipped += 1
                    continue
                existing_titles.add(normalized_title)
                subtitles.append(entry["description"])
                pending_subjects.append(
                    Subject(
                        section=section,
                        title=entry["title"],
                        description=entry["description"],
                        color=form.cleaned_data["color"],
                        weekly_goal_minutes=form.cleaned_data["weekly_goal_minutes"],
                        priority=form.cleaned_data["priority"],
                    )
                )

            with transaction.atomic():
                Subject.objects.bulk_create(pending_subjects)
                _remember_subject_subtitles(section, subtitles)
                _record_subject_action(
                    request.user,
                    section,
                    "create",
                    [subject.id for subject in pending_subjects],
                )

            if pending_subjects:
                summary = f"Added {len(pending_subjects)} subject(s)."
                if skipped:
                    summary += f" Skipped {skipped} duplicate(s)."
                messages.success(request, summary)
            else:
                messages.info(
                    request,
                    "No new subjects were added because every name already exists.",
                )
            return redirect("topics:section_detail", section_id=section.id)
    else:
        form = BulkSubjectForm()

    return render(
        request,
        "topics/bulk_add_subjects.html",
        {
            "form": form,
            "section": section,
            "subtitle_history": _subject_subtitle_history(section),
            "current_topic": section.topic_id,
            "current_section": section.id,
        },
    )


@login_required
@require_POST
def clear_subject_subtitle_history(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    deleted_count, _ = section.subtitle_presets.all().delete()
    if deleted_count:
        messages.success(request, "Saved subtitles cleared.")
    else:
        messages.info(request, "There were no saved subtitles to clear.")

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("topics:add_subject", section_id=section.id)

@login_required
def subject_detail(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )

    return render(
        request,
        "topics/subject_detail.html",
        {
            "subject": subject,
            "notes": subject.notes.all().order_by("-is_pinned", "-updated_at", "-id"),
            "current_topic": subject.section.topic.id,
            "current_section": subject.section.id,
            "current_subject": subject.id,
            "current_activity_type": "notes",
        },
    )


@login_required
def subject_overview(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    focus_snapshot = _focus_snapshot(request.user)
    _add_focus_to_subjects([subject], focus_snapshot)
    completed_sessions = StudySession.objects.filter(
        user=request.user,
        completed=True,
        status="completed",
    )
    timer_snapshot = aggregate_sessions(
        completed_sessions.filter(entry_source="timer")
    )
    manual_snapshot = aggregate_sessions(
        completed_sessions.filter(entry_source="manual")
    )
    timer_seconds = timer_snapshot["totals"]["subject"].get(subject.id, 0)
    manual_seconds = manual_snapshot["totals"]["subject"].get(subject.id, 0)
    user_timezone = _user_timezone(request.user)
    manual_focus_entries = list(
        completed_sessions.filter(
            entry_source="manual",
            subject=subject,
        ).order_by("-ended_at", "-id")
    )
    for entry in manual_focus_entries:
        entry.manual_hours, entry.manual_minutes = divmod(
            round(entry.duration_seconds / 60),
            60,
        )
        entry.manual_date = entry.ended_at.astimezone(user_timezone).date()
        entry.manual_duration = format_duration(entry.duration_seconds)

    return render(
        request,
        "topics/subject_overview.html",
        {
            "subject": subject,
            "note_count": subject.notes.count(),
            "flashcard_count": subject.flashcards.count(),
            "timer_focus_duration": format_duration(timer_seconds),
            "manual_focus_duration": format_duration(manual_seconds),
            "manual_focus_entries": manual_focus_entries,
            "manual_focus_today": timezone.now().astimezone(user_timezone).date(),
            "manage_time_open": request.GET.get("manage_time") == "1",
            "current_topic": subject.section.topic_id,
            "current_section": subject.section_id,
            "current_subject": subject.id,
            "current_activity_type": "general",
        },
    )

@login_required
def edit_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )

    if request.method == "POST":

        form = SubjectForm(
            request.POST,
            instance=subject,
        )

        if form.is_valid():

            subject = form.save()
            _remember_subject_subtitles(subject.section, [subject.description])

            return redirect(
                "topics:section_detail",
                section_id=subject.section.id,
            )

    else:

        form = SubjectForm(instance=subject)

    return render(
        request,
        "topics/edit_subject.html",
        {
            "form": form,
            "subject": subject,
            "subtitle_history": _subject_subtitle_history(subject.section),
        },
    )

@login_required
def delete_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )

    if request.method == "POST":

        section = subject.section
        with transaction.atomic():
            _set_subjects_deleted(section, [subject.id], True)
            _record_subject_action(request.user, section, "delete", [subject.id])
        messages.success(request, f'"{subject.title}" deleted. You can undo this action.')

        return redirect(
            "topics:section_detail",
            section_id=section.id,
        )

    return render(
        request,
        "topics/delete_subject.html",
        {
            "subject": subject,
        },
    )


@login_required
@require_POST
def bulk_delete_subjects(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    try:
        requested_ids = {
            int(value) for value in request.POST.getlist("subject_ids")
        }
    except (TypeError, ValueError):
        requested_ids = set()

    subject_ids = list(
        section.subjects.filter(id__in=requested_ids).values_list("id", flat=True)
    )
    if not subject_ids:
        messages.info(request, "Select at least one subject to delete.")
        return redirect("topics:section_detail", section_id=section.id)

    with transaction.atomic():
        _set_subjects_deleted(section, subject_ids, True)
        _record_subject_action(request.user, section, "delete", subject_ids)
    messages.success(
        request,
        f"Deleted {len(subject_ids)} subject(s). You can undo this action.",
    )
    return redirect("topics:section_detail", section_id=section.id)


@login_required
@require_POST
def undo_subject_action(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    with transaction.atomic():
        action = (
            section.subject_history_actions.select_for_update()
            .filter(user=request.user, is_undone=False)
            .order_by("-created_at", "-id")
            .first()
        )
        if not action:
            messages.info(request, "There is nothing to undo.")
            return redirect("topics:section_detail", section_id=section.id)

        should_delete = action.action_type == "create"
        changed = _set_subjects_deleted(section, action.subject_ids, should_delete)
        action.is_undone = True
        action.save(update_fields=["is_undone"])

    verb = "addition" if action.action_type == "create" else "deletion"
    messages.success(request, f"Undid the last {verb} ({changed} subject(s)).")
    return redirect("topics:section_detail", section_id=section.id)


@login_required
@require_POST
def redo_subject_action(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )
    with transaction.atomic():
        action = (
            section.subject_history_actions.select_for_update()
            .filter(user=request.user, is_undone=True)
            .order_by("created_at", "id")
            .first()
        )
        if not action:
            messages.info(request, "There is nothing to redo.")
            return redirect("topics:section_detail", section_id=section.id)

        should_delete = action.action_type == "delete"
        changed = _set_subjects_deleted(section, action.subject_ids, should_delete)
        action.is_undone = False
        action.save(update_fields=["is_undone"])

    verb = "addition" if action.action_type == "create" else "deletion"
    messages.success(request, f"Redid the last {verb} ({changed} subject(s)).")
    return redirect("topics:section_detail", section_id=section.id)

@login_required
def toggle_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )

    subject.completed = not subject.completed
    subject.save(update_fields=["completed"])

    section_url = reverse("topics:section_detail", args=[subject.section_id])
    return redirect(f"{section_url}#subject-{subject.id}")


@login_required
@require_POST
def log_subject_time(request, subject_id):
    subject = get_object_or_404(
        Subject.objects.select_related("section", "section__topic"),
        id=subject_id,
        section__topic__user=request.user,
    )
    try:
        duration_seconds = _manual_focus_duration(request)
        ended_at = _manual_focus_ended_at(request)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect(_manual_focus_redirect(subject))

    StudySession.objects.create(
        user=request.user,
        topic=subject.section.topic,
        section=subject.section,
        subject=subject,
        started_at=ended_at - timedelta(seconds=duration_seconds),
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        planned_duration_seconds=0,
        paused_seconds=0,
        status="completed",
        activity_type="general",
        entry_source="manual",
        topic_title=subject.section.topic.title,
        section_title=subject.section.title,
        subject_title=subject.title,
        completed=True,
    )

    messages.success(
        request,
        f"Added {format_duration(duration_seconds)} to {subject.title}.",
    )
    return redirect(_manual_focus_redirect(subject))


@login_required
@require_POST
def edit_subject_time(request, subject_id, session_id):
    subject = get_object_or_404(
        Subject.objects.select_related("section", "section__topic"),
        id=subject_id,
        section__topic__user=request.user,
    )
    session = get_object_or_404(
        StudySession,
        id=session_id,
        user=request.user,
        subject=subject,
        entry_source="manual",
        completed=True,
        status="completed",
    )
    try:
        duration_seconds = _manual_focus_duration(request)
        ended_at = _manual_focus_ended_at(request)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect(_manual_focus_redirect(subject))

    session.duration_seconds = duration_seconds
    session.ended_at = ended_at
    session.started_at = ended_at - timedelta(seconds=duration_seconds)
    session.topic = subject.section.topic
    session.section = subject.section
    session.subject = subject
    session.topic_title = subject.section.topic.title
    session.section_title = subject.section.title
    session.subject_title = subject.title
    session.save(update_fields=[
        "duration_seconds",
        "ended_at",
        "started_at",
        "topic",
        "section",
        "subject",
        "topic_title",
        "section_title",
        "subject_title",
    ])
    messages.success(
        request,
        f"Updated manual time for {subject.title} to {format_duration(duration_seconds)}.",
    )
    return redirect(_manual_focus_redirect(subject))


@login_required
@require_POST
def delete_subject_time(request, subject_id, session_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )
    session = get_object_or_404(
        StudySession,
        id=session_id,
        user=request.user,
        subject=subject,
        entry_source="manual",
        completed=True,
        status="completed",
    )
    deleted_duration = format_duration(session.duration_seconds)
    session.delete()
    messages.success(
        request,
        f"Removed {deleted_duration} of manual time from {subject.title}.",
    )
    return redirect(_manual_focus_redirect(subject))

@login_required
def search(request):

    query = request.GET.get("q", "").strip()

    if not query:
        return render(
            request,
            "topics/search_results.html",
            {
                "query": "",
                "topics": Topic.objects.none(),
                "sections": Section.objects.none(),
                "subjects": Subject.objects.none(),
                "flashcards": Flashcard.objects.none(),
                "notes": Note.objects.none(),
            },
        )

    topics = Topic.objects.filter(
        user=request.user,
        title__icontains=query,
    )

    sections = Section.objects.filter(
        topic__user=request.user,
    ).filter(
        Q(title__icontains=query) |
        Q(description__icontains=query)
    )

    subjects = Subject.objects.filter(
        section__topic__user=request.user,
    ).filter(
        Q(title__icontains=query) |
        Q(description__icontains=query)
    )

    flashcards = Flashcard.objects.filter(
        Q(section__topic__user=request.user) |
        Q(
            subject__is_deleted=False,
            subject__section__topic__user=request.user,
        )
    ).filter(
        Q(question__icontains=query) |
        Q(answer__icontains=query)
    ).distinct()

    notes = Note.objects.filter(
        Q(section__isnull=False) | Q(subject__is_deleted=False),
        owner=request.user,
    ).filter(
        Q(title__icontains=query) |
        Q(content__icontains=query)
    )

    return render(
        request,
        "topics/search_results.html",
        {
            "query": query,
            "topics": topics,
            "sections": sections,
            "subjects": subjects,
            "flashcards": flashcards,
            "notes": notes,
        },
    )

@login_required
def dashboard(request):
    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    pinned_dashboard_widgets = _dashboard_widget_preferences(
        preferences,
        "dashboard_pinned_widgets",
    )
    expanded_dashboard_widgets = _dashboard_widget_preferences(
        preferences,
        "dashboard_expanded_widgets",
    )
    try:
        user_timezone = ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")
    now = timezone.now().astimezone(user_timezone)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    today_start = datetime.combine(today, time.min, tzinfo=user_timezone)
    tomorrow_start = today_start + timedelta(days=1)
    week_start_at = datetime.combine(week_start, time.min, tzinfo=user_timezone)
    week_end_at = week_start_at + timedelta(days=7)

    completed_sessions = StudySession.objects.filter(
        user=request.user,
        completed=True,
        status="completed",
    )
    dashboard_recent_sessions = completed_sessions
    if preferences.dashboard_activity_hidden_before:
        dashboard_recent_sessions = dashboard_recent_sessions.filter(
            ended_at__gt=preferences.dashboard_activity_hidden_before,
        )
    today_seconds = completed_sessions.filter(
        ended_at__gte=today_start,
        ended_at__lt=tomorrow_start,
    ).aggregate(total=Sum("duration_seconds"))["total"] or 0
    week_sessions = completed_sessions.filter(
        ended_at__gte=week_start_at,
        ended_at__lt=week_end_at,
    )
    week_seconds = week_sessions.aggregate(total=Sum("duration_seconds"))["total"] or 0

    rhythm = _build_focus_rhythm(
        completed_sessions,
        user_timezone,
        today,
        request.GET.get("rhythm", "7d"),
    )

    completed_days = sorted({
        ended_at.astimezone(user_timezone).date()
        for ended_at in completed_sessions.exclude(ended_at=None)
        .order_by("-ended_at")
        .values_list("ended_at", flat=True)[:400]
    }, reverse=True)
    streak = 0
    expected_day = today
    if completed_days and completed_days[0] == today - timedelta(days=1):
        expected_day = today - timedelta(days=1)
    for day in completed_days:
        if day == expected_day:
            streak += 1
            expected_day -= timedelta(days=1)
        elif day < expected_day:
            break

    owned_cards = Flashcard.objects.filter(
        Q(section__topic__user=request.user)
        | Q(
            subject__is_deleted=False,
            subject__section__topic__user=request.user,
        )
    ).distinct()
    due_flashcards = owned_cards.filter(
        Q(next_review_at__lte=now)
        | Q(next_review_at__isnull=True, learned=False)
    ).count()

    focus = build_focus_analytics(
        request.user,
        completed_sessions,
        week_sessions,
        now,
        week_start_at,
        completed_sessions,
    )
    user_topics = list(
        Topic.objects.filter(user=request.user)
        .prefetch_related("sections__subjects")
    )
    focus_by_topic = focus["tree"]
    needs_attention = focus["attention"]

    recent_session = (
        completed_sessions
        .select_related("topic", "section", "subject")
        .order_by("-ended_at")
        .first()
    )
    milestone_priority_order = {"high": 0, "normal": 1, "low": 2}
    milestones = list(Milestone.objects.filter(user=request.user, completed=False))
    milestones.sort(
        key=lambda milestone: (
            milestone_priority_order.get(milestone.priority, 1),
            milestone.target_at is None,
            milestone.target_at or now,
            -milestone.id,
        )
    )
    task_priority_order = {"high": 0, "normal": 1, "low": 2}
    tasks = list(
        Task.objects.filter(user=request.user, completed=False)
        .select_related("topic", "section", "subject")
    )
    tasks.sort(
        key=lambda task: (
            not task.is_pinned,
            task_priority_order.get(task.priority, 1),
            task.due_date is None,
            task.due_date or today,
            task.created_at,
        )
    )
    today_goal = max(1, preferences.daily_focus_goal_minutes)
    weekly_goal = max(1, preferences.weekly_focus_goal_minutes)
    context = {
        "topics": user_topics,
        "is_new_user": not completed_sessions.exists(),
        "today_minutes": round(today_seconds / 60),
        "today_goal": today_goal,
        "today_progress": min(100, round((today_seconds / 60) / today_goal * 100)),
        "week_minutes": round(week_seconds / 60),
        "week_goal": weekly_goal,
        "week_progress": min(100, round((week_seconds / 60) / weekly_goal * 100)),
        "week_sessions_count": week_sessions.count(),
        "streak": streak,
        "due_flashcards": due_flashcards,
        "weekly_chart": rhythm["chart"],
        "rhythm_chart": rhythm["chart"],
        "rhythm_period": rhythm["period"],
        "rhythm_label": rhythm["label"],
        "rhythm_aria_label": rhythm["aria_label"],
        "rhythm_total_minutes": rhythm["total_minutes"],
        "focus_by_topic": focus_by_topic[:6],
        "needs_attention": needs_attention[:4],
        "recent_session": recent_session,
        "recent_session_resume_url": _study_session_resume_url(recent_session),
        "recent_session_minutes": round(recent_session.duration_seconds / 60) if recent_session else 0,
        "recent_sessions": dashboard_recent_sessions.select_related("topic", "section", "subject").order_by("-ended_at")[:6],
        "has_focus_history": completed_sessions.exists(),
        "recent_notes": Note.objects.filter(
            Q(section__isnull=False) | Q(subject__is_deleted=False),
            owner=request.user,
        ).order_by("-updated_at")[:4],
        "pinned_notes": Note.objects.filter(
            Q(section__isnull=False) | Q(subject__is_deleted=False),
            owner=request.user,
            is_pinned=True,
        ).order_by("-updated_at")[:5],
        "quick_notes": QuickNote.objects.filter(
            owner=request.user,
            deleted_at__isnull=True,
        ).order_by("-is_pinned", "-updated_at")[:3],
        "tasks": tasks[:10],
        "milestones": milestones[:5],
        "milestone_active_total": len(milestones),
        "milestone_more_count": max(0, len(milestones) - 5),
        "task_topics": user_topics,
        "today": today,
        "user_timezone_name": getattr(user_timezone, "key", "UTC"),
        "pinned_dashboard_widgets": pinned_dashboard_widgets,
        "expanded_dashboard_widgets": expanded_dashboard_widgets,
        "has_pinned_dashboard_widgets": bool(pinned_dashboard_widgets),
        "has_unpinned_dashboard_widgets": len(pinned_dashboard_widgets) < len(DASHBOARD_WIDGETS),
    }
    return render(request, "dashboard.html", context)


@login_required
@require_POST
def toggle_dashboard_widget(request, widget, preference):
    if widget not in DASHBOARD_WIDGETS or preference not in {"pin", "expand"}:
        return HttpResponseBadRequest("Unknown dashboard widget preference.")

    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    field_name = {
        "pin": "dashboard_pinned_widgets",
        "expand": "dashboard_expanded_widgets",
    }[preference]
    saved_widgets = _dashboard_widget_preferences(preferences, field_name)

    if widget in saved_widgets:
        saved_widgets.remove(widget)
    else:
        saved_widgets.append(widget)

    # Keep the display order stable regardless of the order the controls were used.
    saved_widgets = [item for item in DASHBOARD_WIDGETS if item in saved_widgets]
    setattr(preferences, field_name, saved_widgets)
    preferences.save(update_fields=[field_name])
    return redirect("topics:home")


@login_required
def analytics(request):
    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    try:
        user_timezone = ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")

    now = timezone.now().astimezone(user_timezone)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    week_start_at = datetime.combine(week_start, time.min, tzinfo=user_timezone)
    week_end_at = week_start_at + timedelta(days=7)

    period = request.GET.get("period", "week")
    if period not in {"week", "30d", "all"}:
        period = "week"

    completed_sessions = StudySession.objects.filter(
        user=request.user,
        completed=True,
        status="completed",
    )
    week_sessions = completed_sessions.filter(
        ended_at__gte=week_start_at,
        ended_at__lt=week_end_at,
    )

    if period == "30d":
        period_start = datetime.combine(
            today - timedelta(days=29),
            time.min,
            tzinfo=user_timezone,
        )
        period_sessions = completed_sessions.filter(ended_at__gte=period_start)
        period_label = "Last 30 days"
    elif period == "all":
        period_sessions = completed_sessions
        period_label = "All time"
    else:
        period_sessions = week_sessions
        period_label = "This week"

    focus = build_focus_analytics(
        request.user,
        period_sessions,
        week_sessions,
        now,
        week_start_at,
        completed_sessions,
    )
    return render(request, "topics/analytics.html", {
        **focus,
        "period": period,
        "period_label": period_label,
        "show_goal_progress": period == "week",
        "attention": focus["attention"][:8],
    })
