import calendar
from collections import Counter
from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from users.models import UserPreferences

from .forms import MilestoneForm, TaskForm
from .models import Milestone, Task


def _user_timezone(user):
    preferences, _ = UserPreferences.objects.get_or_create(user=user)
    try:
        return ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _journal_redirect(request):
    if request.POST.get("return_to") != "journal":
        return redirect("topics:home")

    selected_date = parse_date(request.POST.get("journal_date", ""))
    journal_url = reverse("planner:task_journal")
    if selected_date:
        journal_url = f"{journal_url}?date={selected_date.isoformat()}"
    return redirect(journal_url)


def _milestone_redirect(request):
    if request.POST.get("return_to") == "milestones":
        return redirect("planner:milestone_hub")
    return redirect("topics:home")


def _sorted_milestones(milestones):
    priority_order = {"high": 0, "normal": 1, "low": 2}
    now = timezone.now()
    return sorted(
        milestones,
        key=lambda milestone: (
            priority_order.get(milestone.priority, 1),
            milestone.target_at is None,
            milestone.target_at or now,
            -milestone.id,
        ),
    )


def _month_after(month_start):
    return (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )


@login_required
@require_POST
def add_task(request):
    form = TaskForm(request.POST, user=request.user)
    if form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        messages.success(
            request,
            "Study plan added." if task.is_study_task else "Task added.",
        )
    else:
        error_text = " ".join(
            error
            for errors in form.errors.values()
            for error in errors
        )
        messages.error(request, error_text or "The task could not be added.")
    return redirect("topics:home")


@login_required
@require_POST
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    previous_study_signature = (
        task.topic_id,
        task.section_id,
        task.subject_id,
        task.activity_type,
        task.target_minutes,
    )
    form = TaskForm(request.POST, user=request.user, instance=task)
    if form.is_valid():
        task = form.save(commit=False)
        current_study_signature = (
            task.topic_id,
            task.section_id,
            task.subject_id,
            task.activity_type,
            task.target_minutes,
        )
        if current_study_signature != previous_study_signature:
            task.focused_seconds = 0
            if task.completed_by_focus:
                task.completed = False
                task.completed_at = None
            task.completed_by_focus = False
        task.save()
        messages.success(request, "To-do updated.")
    else:
        error_text = " ".join(
            error
            for errors in form.errors.values()
            for error in errors
        )
        messages.error(request, error_text or "The to-do could not be updated.")
    return redirect("topics:home")


@login_required
@require_POST
def toggle_task_pin(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.is_pinned = not task.is_pinned
    task.save(update_fields=["is_pinned"])
    return redirect("topics:home")


@login_required
@require_POST
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    completing = not task.completed
    task.mark_manually(completing)
    if completing:
        task.completion_note = request.POST.get("completion_note", "").strip()[:2000]
    task.save(
        update_fields=[
            "completed",
            "completed_at",
            "completed_by_focus",
            "completion_note",
        ]
    )
    messages.success(
        request,
        "Added to your to-do journal." if completing else "Task restored to your to-do list.",
    )
    return _journal_redirect(request)


@login_required
@require_POST
def update_task_reflection(request, task_id):
    task = get_object_or_404(
        Task,
        id=task_id,
        user=request.user,
        completed=True,
    )
    task.completion_note = request.POST.get("completion_note", "").strip()[:2000]
    task.save(update_fields=["completion_note"])
    messages.success(request, "Journal reflection updated.")
    return _journal_redirect(request)


@login_required
@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    messages.success(request, "Task permanently deleted.")
    return _journal_redirect(request)


@login_required
def task_journal(request):
    user_timezone = _user_timezone(request.user)
    local_today = timezone.now().astimezone(user_timezone).date()
    selected_date = parse_date(request.GET.get("date", "")) or local_today
    month_start = selected_date.replace(day=1)
    next_month_start = _month_after(month_start)
    previous_month = (month_start - timedelta(days=1)).replace(day=1)

    month_start_at = datetime.combine(month_start, time.min, tzinfo=user_timezone)
    next_month_at = datetime.combine(next_month_start, time.min, tzinfo=user_timezone)
    month_tasks = list(
        Task.objects.filter(
            user=request.user,
            completed=True,
            completed_at__gte=month_start_at,
            completed_at__lt=next_month_at,
        )
        .select_related("topic", "section", "subject")
        .order_by("-completed_at")
    )
    completion_counts = Counter(
        timezone.localtime(task.completed_at, user_timezone).date()
        for task in month_tasks
        if task.completed_at
    )
    selected_tasks = []
    for task in month_tasks:
        task.completed_local = timezone.localtime(task.completed_at, user_timezone)
        if task.completed_local.date() == selected_date:
            selected_tasks.append(task)

    month_calendar = calendar.Calendar(firstweekday=0)
    calendar_weeks = []
    for week in month_calendar.monthdatescalendar(month_start.year, month_start.month):
        calendar_weeks.append(
            [
                {
                    "date": day,
                    "date_iso": day.isoformat(),
                    "day": day.day,
                    "in_month": day.month == month_start.month,
                    "is_today": day == local_today,
                    "is_selected": day == selected_date,
                    "completed_count": completion_counts.get(day, 0),
                }
                for day in week
            ]
        )

    context = {
        "selected_date": selected_date,
        "selected_tasks": selected_tasks,
        "calendar_weeks": calendar_weeks,
        "month_label": month_start.strftime("%B %Y"),
        "previous_month_date": previous_month.isoformat(),
        "next_month_date": next_month_start.isoformat(),
        "completed_tasks_total": Task.objects.filter(
            user=request.user,
            completed=True,
        ).count(),
        "user_timezone_name": getattr(user_timezone, "key", "UTC"),
    }
    return render(request, "planner/task_journal.html", context)


@login_required
def milestone_hub(request):
    milestones = list(Milestone.objects.filter(user=request.user))
    active_milestones = _sorted_milestones(
        milestone for milestone in milestones if not milestone.completed
    )
    completed_milestones = sorted(
        (milestone for milestone in milestones if milestone.completed),
        key=lambda milestone: milestone.completed_at or milestone.created_at,
        reverse=True,
    )
    user_timezone = _user_timezone(request.user)
    for milestone in active_milestones + completed_milestones:
        milestone.target_local_input = (
            milestone.target_at.astimezone(user_timezone).strftime("%Y-%m-%dT%H:%M")
            if milestone.target_at
            else ""
        )
    context = {
        "active_milestones": active_milestones,
        "completed_milestones": completed_milestones,
        "active_count": len(active_milestones),
        "completed_count": len(completed_milestones),
        "overdue_count": sum(item.target_has_passed for item in active_milestones),
        "user_timezone_name": getattr(user_timezone, "key", "UTC"),
    }
    return render(request, "planner/milestone_hub.html", context)


@login_required
@require_POST
def add_milestone(request):
    with timezone.override(_user_timezone(request.user)):
        form = MilestoneForm(request.POST)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.user = request.user
            milestone.save()
            messages.success(
                request,
                "Deadline added." if milestone.kind == "deadline" else "Plan added.",
            )
        else:
            error_text = " ".join(
                error
                for errors in form.errors.values()
                for error in errors
            )
            messages.error(
                request,
                error_text or "The plan could not be added.",
            )
    return _milestone_redirect(request)


@login_required
@require_POST
def toggle_milestone(request, milestone_id):
    milestone = get_object_or_404(
        Milestone,
        id=milestone_id,
        user=request.user,
    )
    milestone.mark_manually(not milestone.completed)
    milestone.save(update_fields=["completed", "completed_at"])
    messages.success(
        request,
        "Moved to completed plans." if milestone.completed else "Plan restored.",
    )
    return _milestone_redirect(request)


@login_required
@require_POST
def update_milestone(request, milestone_id):
    milestone = get_object_or_404(
        Milestone,
        id=milestone_id,
        user=request.user,
    )
    with timezone.override(_user_timezone(request.user)):
        form = MilestoneForm(request.POST, instance=milestone)
        if form.is_valid():
            form.save()
            messages.success(request, "Plan updated.")
        else:
            error_text = " ".join(
                error
                for errors in form.errors.values()
                for error in errors
            )
            messages.error(request, error_text or "The plan could not be updated.")
    return _milestone_redirect(request)


@login_required
@require_POST
def update_milestone_priority(request, milestone_id):
    milestone = get_object_or_404(
        Milestone,
        id=milestone_id,
        user=request.user,
    )
    priority = request.POST.get("priority", "")
    valid_priorities = {value for value, _ in Milestone.PRIORITY_CHOICES}
    if priority not in valid_priorities:
        messages.error(request, "Choose a valid importance.")
    else:
        milestone.priority = priority
        milestone.save(update_fields=["priority"])
    return _milestone_redirect(request)


@login_required
@require_POST
def delete_milestone(request, milestone_id):
    milestone = get_object_or_404(
        Milestone,
        id=milestone_id,
        user=request.user,
    )
    milestone.delete()
    messages.success(request, "Plan permanently deleted.")
    return _milestone_redirect(request)
