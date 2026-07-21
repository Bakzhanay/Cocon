import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0004_studysession_task"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudySessionSegment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "activity_type",
                    models.CharField(
                        choices=[
                            ("general", "General study"),
                            ("notes", "Notes"),
                            ("flashcards", "Flashcards"),
                            ("reading", "Reading"),
                        ],
                        default="general",
                        max_length=12,
                    ),
                ),
                ("topic_title", models.CharField(blank=True, max_length=100)),
                ("section_title", models.CharField(blank=True, max_length=100)),
                ("subject_title", models.CharField(blank=True, max_length=100)),
                ("started_offset_seconds", models.PositiveIntegerField(default=0)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "section",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="topics.section",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="segments",
                        to="study.studysession",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="topics.subject",
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="topics.topic",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
    ]
