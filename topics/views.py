from django.utils import timezone
from django.db.models import Sum
from study.models import StudySession
from study.analytics import build_focus_analytics
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Topic, Section, Subject
from .forms import TopicForm, SectionForm, SubjectForm

from flashcards.models import Flashcard
from notes.models import Note, QuickNote
from planner.models import Task
from users.models import UserPreferences

from django.db.models import Q

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
def topic_detail(request, topic_id):

    topic = get_object_or_404(
        Topic,
        id=topic_id,
        user=request.user,
    )

    sections = (
    topic.sections
    .annotate(
        subject_count=Count("subjects")
    )
    .order_by("title")
    )

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

    subjects = section.subjects.all()
    total_subjects = subjects.count()
    completed_subjects = subjects.filter(completed=True).count()

    return render(
        request,
        "topics/section_detail.html",
        {
            "section": section,
            "subjects": subjects,
            "total_subjects": total_subjects,
            "completed_subjects": completed_subjects,
            "subjects_progress": round((completed_subjects / total_subjects) * 100) if total_subjects else 0,
            "notes": section.notes.all().order_by("-updated_at"),
            "current_topic": section.topic.id,
            "current_section": section.id,
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
        },
    )

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
            "notes": subject.notes.all().order_by("-updated_at"),
            "current_topic": subject.section.topic.id,
            "current_section": subject.section.id,
            "current_subject": subject.id,
            "current_activity_type": "notes",
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

            form.save()

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

        section_id = subject.section.id

        subject.delete()

        return redirect(
            "topics:section_detail",
            section_id=section_id,
        )

    return render(
        request,
        "topics/delete_subject.html",
        {
            "subject": subject,
        },
    )

@login_required
def toggle_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )

    subject.completed = not subject.completed
    subject.save()

    return redirect(
        "topics:section_detail",
        section_id=subject.section.id,
    )

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
        title__icontains=query,
    )

    subjects = Subject.objects.filter(
        section__topic__user=request.user,
        title__icontains=query,
    )

    flashcards = Flashcard.objects.filter(
        Q(section__topic__user=request.user) |
        Q(subject__section__topic__user=request.user)
    ).filter(
        Q(question__icontains=query) |
        Q(answer__icontains=query)
    ).distinct()

    notes = Note.objects.filter(
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
    chart_start = today - timedelta(days=6)
    chart_start_at = datetime.combine(chart_start, time.min, tzinfo=user_timezone)

    completed_sessions = StudySession.objects.filter(
        user=request.user,
        completed=True,
        status="completed",
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

    chart_sessions = completed_sessions.filter(
        ended_at__gte=chart_start_at,
        ended_at__lt=tomorrow_start,
    )
    daily_totals = {}
    for ended_at, duration in chart_sessions.values_list("ended_at", "duration_seconds"):
        local_day = ended_at.astimezone(user_timezone).date()
        daily_totals[local_day] = daily_totals.get(local_day, 0) + duration
    weekly_chart = []
    max_daily_seconds = max([*daily_totals.values(), 1])
    for offset in range(7):
        day = chart_start + timedelta(days=offset)
        seconds = daily_totals.get(day, 0)
        weekly_chart.append({
            "date": day,
            "label": day.strftime("%a"),
            "minutes": round(seconds / 60),
            "height": max(4, round((seconds / max_daily_seconds) * 100)) if seconds else 4,
            "is_today": day == today,
        })

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
        | Q(subject__section__topic__user=request.user)
    ).distinct()
    due_flashcards = owned_cards.filter(
        Q(next_review_at__lte=now)
        | Q(next_review_at__isnull=True, learned=False)
    ).count()

    focus = build_focus_analytics(
        request.user,
        week_sessions,
        week_sessions,
        now,
        week_start_at,
        completed_sessions,
    )
    user_topics = list(Topic.objects.filter(user=request.user))
    focus_by_topic = focus["tree"]
    needs_attention = focus["attention"]

    recent_session = (
        completed_sessions
        .select_related("topic", "section", "subject")
        .order_by("-ended_at")
        .first()
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
        "weekly_chart": weekly_chart,
        "focus_by_topic": focus_by_topic[:6],
        "needs_attention": needs_attention[:4],
        "recent_session": recent_session,
        "recent_session_minutes": round(recent_session.duration_seconds / 60) if recent_session else 0,
        "recent_sessions": completed_sessions.select_related("topic", "section", "subject").order_by("-ended_at")[:6],
        "recent_notes": Note.objects.filter(owner=request.user).order_by("-updated_at")[:4],
        "pinned_notes": Note.objects.filter(owner=request.user, is_pinned=True).order_by("-updated_at")[:5],
        "quick_notes": QuickNote.objects.filter(owner=request.user).order_by("-is_pinned", "-updated_at")[:3],
        "tasks": Task.objects.filter(user=request.user).order_by("completed", "due_date", "-created_at")[:10],
        "today": today,
    }
    return render(request, "dashboard.html", context)


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
