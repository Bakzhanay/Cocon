from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Max, Sum
from django.urls import reverse

from topics.models import Topic

from .models import StudySessionSegment


ACTIVITY_LABELS = {
    "notes": "Notes",
    "flashcards": "Flashcards",
    "reading": "Reading",
    "general": "General focus",
}
ACTIVITY_ORDER = ("notes", "flashcards", "reading", "general")
PRIORITY_WEIGHT = {"high": 1.35, "normal": 1.0, "low": 0.75}


def format_duration(seconds):
    minutes = max(0, round((seconds or 0) / 60))
    if minutes < 60:
        return f"{minutes} min"
    hours, remaining = divmod(minutes, 60)
    return f"{hours} h" if not remaining else f"{hours} h {remaining} min"


def _latest(current, candidate):
    if candidate is None:
        return current
    if current is None or candidate > current:
        return candidate
    return current


def aggregate_sessions(sessions):
    summary = sessions.aggregate(
        total_seconds=Sum("duration_seconds"),
        session_count=Count("id"),
    )
    segment_session_ids = StudySessionSegment.objects.filter(
        session_id__in=sessions.values("id")
    ).values("session_id")
    legacy_rows = sessions.exclude(id__in=segment_session_ids).values(
        "topic_id",
        "section_id",
        "subject_id",
        "activity_type",
    ).annotate(
        total_seconds=Sum("duration_seconds"),
        last_at=Max("ended_at"),
    )
    segment_rows = StudySessionSegment.objects.filter(
        session_id__in=sessions.values("id")
    ).values(
        "topic_id",
        "section_id",
        "subject_id",
        "activity_type",
    ).annotate(
        total_seconds=Sum("duration_seconds"),
        last_at=Max("session__ended_at"),
    )

    totals = {
        "topic": defaultdict(int),
        "section": defaultdict(int),
        "subject": defaultdict(int),
    }
    latest = {
        "topic": {},
        "section": {},
        "subject": {},
    }
    activities = {
        "topic_direct": defaultdict(int),
        "section_direct": defaultdict(int),
        "subject": defaultdict(int),
        "general": defaultdict(int),
    }
    for row in [*legacy_rows, *segment_rows]:
        seconds = row["total_seconds"] or 0
        activity_type = row["activity_type"] or "general"

        for level in ("topic", "section", "subject"):
            object_id = row[f"{level}_id"]
            if object_id:
                totals[level][object_id] += seconds
                latest[level][object_id] = _latest(
                    latest[level].get(object_id),
                    row["last_at"],
                )

        if row["subject_id"]:
            activities["subject"][(row["subject_id"], activity_type)] += seconds
        elif row["section_id"]:
            activities["section_direct"][(row["section_id"], activity_type)] += seconds
        elif row["topic_id"]:
            activities["topic_direct"][(row["topic_id"], activity_type)] += seconds
        else:
            activities["general"][activity_type] += seconds

    return {
        "totals": totals,
        "latest": latest,
        "activities": activities,
        "total_seconds": summary["total_seconds"] or 0,
        "session_count": summary["session_count"] or 0,
    }


def _activity_rows(activity_totals, object_id=None):
    rows = []
    for activity_type in ACTIVITY_ORDER:
        key = (object_id, activity_type) if object_id is not None else activity_type
        seconds = activity_totals.get(key, 0)
        if seconds:
            rows.append({
                "type": activity_type,
                "label": ACTIVITY_LABELS[activity_type],
                "seconds": seconds,
                "duration": format_duration(seconds),
            })
    return rows


def _pace_metrics(seconds, goal_minutes, priority, now, week_start, last_at):
    actual_minutes = round((seconds or 0) / 60)
    if goal_minutes <= 0:
        return {
            "goal_minutes": 0,
            "week_minutes": actual_minutes,
            "progress": 0,
            "remaining_minutes": 0,
            "expected_minutes": 0,
            "gap_minutes": 0,
            "status": "no-goal",
            "status_label": "No weekly goal",
            "attention_score": 0,
            "attention_message": "",
        }

    week_seconds = timedelta(days=7).total_seconds()
    elapsed_ratio = min(1, max(0, (now - week_start).total_seconds() / week_seconds))
    expected_minutes = round(goal_minutes * elapsed_ratio)
    gap_minutes = max(0, expected_minutes - actual_minutes)
    grace_minutes = max(15, round(goal_minutes * 0.1))
    remaining_minutes = max(0, goal_minutes - actual_minutes)
    progress = min(100, round((actual_minutes / goal_minutes) * 100))

    if actual_minutes >= goal_minutes:
        status = "complete"
        status_label = "Goal complete"
    elif gap_minutes > grace_minutes:
        status = "behind"
        status_label = "Behind pace"
    else:
        status = "on-track"
        status_label = "On track"

    days_since = None
    if last_at:
        days_since = max(0, int((now - last_at).total_seconds() // 86400))

    attention_message = ""
    if status == "behind":
        if last_at is None:
            attention_message = f"No focus yet · {gap_minutes} min behind"
        elif days_since >= 3:
            attention_message = f"No focus for {days_since} days · {gap_minutes} min behind"
        else:
            attention_message = f"{gap_minutes} min behind weekly pace"

    inactivity_bonus = min(0.35, (days_since or 0) * 0.05)
    attention_score = (
        (gap_minutes / max(1, goal_minutes)) + inactivity_bonus
    ) * PRIORITY_WEIGHT.get(priority, 1.0)

    return {
        "goal_minutes": goal_minutes,
        "week_minutes": actual_minutes,
        "progress": progress,
        "remaining_minutes": remaining_minutes,
        "expected_minutes": expected_minutes,
        "gap_minutes": gap_minutes,
        "status": status,
        "status_label": status_label,
        "attention_score": attention_score,
        "attention_message": attention_message,
    }


def build_focus_analytics(
    user,
    period_sessions,
    week_sessions,
    now,
    week_start,
    history_sessions=None,
):
    period = aggregate_sessions(period_sessions)
    week = period if week_sessions is period_sessions else aggregate_sessions(week_sessions)
    history = (
        week
        if history_sessions is None or history_sessions is week_sessions
        else aggregate_sessions(history_sessions)
    )
    topics = list(
        Topic.objects
        .filter(user=user)
        .prefetch_related("sections__subjects")
    )
    attention = []
    tree = []

    for topic in topics:
        section_nodes = []
        derived_topic_goal = 0
        for section in topic.sections.all():
            subject_nodes = []
            derived_section_goal = 0
            for subject in section.subjects.all():
                goal_minutes = subject.weekly_goal_minutes
                derived_section_goal += goal_minutes
                pace = _pace_metrics(
                    week["totals"]["subject"].get(subject.id, 0),
                    goal_minutes,
                    subject.priority,
                    now,
                    week_start,
                    history["latest"]["subject"].get(subject.id),
                )
                subject_node = {
                    "object": subject,
                    "subject": subject,
                    "title": subject.title,
                    "url": reverse("topics:subject_overview", args=[subject.id]),
                    "kind": "Subject",
                    "priority": subject.priority,
                    "seconds": period["totals"]["subject"].get(subject.id, 0),
                    "duration": format_duration(period["totals"]["subject"].get(subject.id, 0)),
                    "activities": _activity_rows(period["activities"]["subject"], subject.id),
                    "goal_is_derived": False,
                    **pace,
                }
                subject_nodes.append(subject_node)
                if pace["status"] == "behind":
                    attention.append(subject_node)

            section_goal = section.weekly_goal_minutes or derived_section_goal
            derived_topic_goal += section_goal
            section_pace = _pace_metrics(
                week["totals"]["section"].get(section.id, 0),
                section_goal,
                section.priority,
                now,
                week_start,
                history["latest"]["section"].get(section.id),
            )
            subject_nodes.sort(key=lambda item: (-item["seconds"], item["title"].lower()))
            section_node = {
                "object": section,
                "section": section,
                "title": section.title,
                "url": reverse("topics:section_detail", args=[section.id]),
                "kind": "Section",
                "priority": section.priority,
                "seconds": period["totals"]["section"].get(section.id, 0),
                "duration": format_duration(period["totals"]["section"].get(section.id, 0)),
                "subjects": subject_nodes,
                "direct_activities": _activity_rows(period["activities"]["section_direct"], section.id),
                "goal_is_derived": not section.weekly_goal_minutes and bool(section_goal),
                **section_pace,
            }
            section_nodes.append(section_node)
            if section.weekly_goal_minutes and section_pace["status"] == "behind":
                attention.append(section_node)

        topic_goal = topic.weekly_goal_minutes or derived_topic_goal
        topic_pace = _pace_metrics(
            week["totals"]["topic"].get(topic.id, 0),
            topic_goal,
            topic.priority,
            now,
            week_start,
            history["latest"]["topic"].get(topic.id),
        )
        section_nodes.sort(key=lambda item: (-item["seconds"], item["title"].lower()))
        topic_node = {
            "object": topic,
            "topic": topic,
            "title": topic.title,
            "url": reverse("topics:topic_detail", args=[topic.id]),
            "kind": "Topic",
            "priority": topic.priority,
            "seconds": period["totals"]["topic"].get(topic.id, 0),
            "duration": format_duration(period["totals"]["topic"].get(topic.id, 0)),
            "sections": section_nodes,
            "direct_activities": _activity_rows(period["activities"]["topic_direct"], topic.id),
            "goal_is_derived": not topic.weekly_goal_minutes and bool(topic_goal),
            **topic_pace,
        }
        tree.append(topic_node)
        if topic_pace["status"] == "behind":
            attention.append(topic_node)

    tree.sort(key=lambda item: (-item["seconds"], item["title"].lower()))
    max_topic_minutes = max([round(item["seconds"] / 60) for item in tree] + [1])
    tracked_nodes = []
    for topic_node in tree:
        topic_node["minutes"] = round(topic_node["seconds"] / 60)
        topic_node["bar_width"] = max(
            3,
            round((topic_node["minutes"] / max_topic_minutes) * 100),
        )
        details = []
        direct_minutes = round(sum(
            item["seconds"] for item in topic_node["direct_activities"]
        ) / 60)
        if direct_minutes:
            details.append(f"Topic-level {direct_minutes}m")
        details.extend(
            f"{section_node['title']} {round(section_node['seconds'] / 60)}m"
            for section_node in topic_node["sections"][:3]
            if section_node["seconds"]
        )
        topic_node["detail"] = " · ".join(details) or "No focus yet"
        if topic_node["goal_minutes"]:
            tracked_nodes.append(topic_node)
        for section_node in topic_node["sections"]:
            if section_node["goal_minutes"]:
                tracked_nodes.append(section_node)
            tracked_nodes.extend(
                subject_node
                for subject_node in section_node["subjects"]
                if subject_node["goal_minutes"]
            )

    attention.sort(key=lambda item: (-item["attention_score"], item["title"].lower()))
    general_activities = _activity_rows(period["activities"]["general"])
    general_seconds = sum(item["seconds"] for item in general_activities)
    most_focused = next((item for item in tree if item["seconds"]), None)

    return {
        "tree": tree,
        "attention": attention,
        "general": {
            "seconds": general_seconds,
            "duration": format_duration(general_seconds),
            "activities": general_activities,
        },
        "total_seconds": period["total_seconds"],
        "total_duration": format_duration(period["total_seconds"]),
        "session_count": period["session_count"],
        "most_focused": most_focused,
        "tracked_count": len(tracked_nodes),
        "on_track_count": sum(
            item["status"] in {"on-track", "complete"}
            for item in tracked_nodes
        ),
        "behind_count": sum(item["status"] == "behind" for item in tracked_nodes),
    }
