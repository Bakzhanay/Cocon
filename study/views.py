import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from topics.models import Section, Subject, Topic
from users.models import UserPreferences
from planner.models import Task

from .models import StudySession


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


@login_required
def start_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    topic_id = data.get("topic_id")
    subject_id = data.get("subject_id")
    section_id = data.get("section_id")
    try:
        planned_duration = int(data.get("planned_duration_seconds") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid planned duration"}, status=400)
    if planned_duration and not 1 <= planned_duration <= 24 * 60 * 60:
        return JsonResponse({"error": "Invalid planned duration"}, status=400)

    activity_type = data.get("activity_type", "general")
    valid_activity_types = {choice[0] for choice in StudySession.ACTIVITY_CHOICES}
    if activity_type not in valid_activity_types:
        activity_type = "general"
    topic = None
    subject = None
    section = None

    if subject_id:
        subject = (
            Subject.objects
            .filter(id=subject_id, section__topic__user=request.user)
            .select_related("section", "section__topic")
            .first()
        )
        if not subject:
            return JsonResponse({"error": "Subject not found"}, status=404)
        section = subject.section
        topic = section.topic

    if section_id:
        requested_section = (
            Section.objects
            .filter(id=section_id, topic__user=request.user)
            .select_related("topic")
            .first()
        )
        if not requested_section:
            return JsonResponse({"error": "Section not found"}, status=404)
        if subject and subject.section_id != requested_section.id:
            return JsonResponse({"error": "Subject and section do not match"}, status=400)
        section = requested_section
        topic = section.topic

    if topic_id:
        requested_topic = Topic.objects.filter(id=topic_id, user=request.user).first()
        if not requested_topic:
            return JsonResponse({"error": "Topic not found"}, status=404)
        if section and section.topic_id != requested_topic.id:
            return JsonResponse({"error": "Topic and section do not match"}, status=400)
        topic = requested_topic

    now = timezone.now()
    StudySession.objects.filter(
        user=request.user,
        completed=False,
        ended_at__isnull=True,
    ).update(ended_at=now, status="cancelled")

    session = StudySession.objects.create(
        user=request.user,
        started_at=now,
        topic=topic,
        subject=subject,
        section=section,
        planned_duration_seconds=planned_duration,
        activity_type=activity_type,
        topic_title=topic.title if topic else "",
        subject_title=subject.title if subject else "",
        section_title=section.title if section else "",
        status="active",
    )
    return JsonResponse({"success": True, "session_id": session.id})


@login_required
def stop_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    session_id = data.get("session_id")
    sessions = StudySession.objects.filter(user=request.user)
    if session_id:
        session = sessions.filter(id=session_id).first()
    else:
        session = (
            sessions
            .filter(completed=False, ended_at__isnull=True)
            .order_by("-started_at")
            .first()
        )

    if not session:
        return JsonResponse({"error": "No active session"}, status=404)

    if session.completed:
        return JsonResponse({
            "success": True,
            "duration": session.duration_seconds,
            "already_completed": True,
        })

    requested_duration = data.get("duration_seconds")
    if requested_duration is not None:
        try:
            requested_duration = int(requested_duration)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid duration"}, status=400)
        if not 1 <= requested_duration <= 24 * 60 * 60:
            return JsonResponse({"error": "Invalid duration"}, status=400)

    session.ended_at = timezone.now()
    session.duration_seconds = requested_duration or max(
        1,
        int((session.ended_at - session.started_at).total_seconds()),
    )
    try:
        session.paused_seconds = max(0, int(data.get("paused_seconds") or 0))
    except (TypeError, ValueError):
        session.paused_seconds = 0
    session.status = "completed"
    session.completed = True
    session.save(update_fields=[
        "ended_at",
        "duration_seconds",
        "paused_seconds",
        "status",
        "completed",
    ])

    return JsonResponse({
        "success": True,
        "duration": session.duration_seconds,
    })


@login_required
def cancel_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    session = StudySession.objects.filter(
        id=data.get("session_id"),
        user=request.user,
    ).first()
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)

    if not session.completed:
        session.ended_at = timezone.now()
        session.duration_seconds = 0
        session.status = "cancelled"
        session.save(update_fields=["ended_at", "duration_seconds", "status"])

    return JsonResponse({"success": True})


@login_required
def activity(request):
    try:
        year = int(request.GET.get("year", timezone.localdate().year))
        month = int(request.GET.get("month", timezone.localdate().month))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid month"}, status=400)

    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return JsonResponse({"error": "Invalid month"}, status=400)

    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    try:
        user_timezone = ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("Asia/Qyzylorda")
    month_start = datetime(year, month, 1, tzinfo=user_timezone)
    next_month = (
        datetime(year + 1, 1, 1, tzinfo=user_timezone)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=user_timezone)
    )
    sessions = StudySession.objects.filter(
        user=request.user,
        completed=True,
        status="completed",
        ended_at__gte=month_start,
        ended_at__lt=next_month,
    ).values_list("ended_at", "duration_seconds")
    days = {}
    for ended_at, duration_seconds in sessions:
        date_key = ended_at.astimezone(user_timezone).date().isoformat()
        item = days.setdefault(date_key, {"date": date_key, "count": 0, "duration_seconds": 0})
        item["count"] += 1
        item["duration_seconds"] += duration_seconds
    tasks = []
    local_today = timezone.now().astimezone(user_timezone).date()
    for task in Task.objects.filter(
        user=request.user,
        due_date__gte=month_start.date(),
        due_date__lt=next_month.date(),
    ).values("due_date", "completed"):
        tasks.append({
            "date": task["due_date"].isoformat(),
            "completed": task["completed"],
            "missed": task["due_date"] < local_today and not task["completed"],
        })

    return JsonResponse({
        "days": [days[key] for key in sorted(days)],
        "tasks": tasks,
    })
