from django.db import migrations, models
import django.db.models.deletion


def seed_subject_subtitle_presets(apps, schema_editor):
    Subject = apps.get_model("topics", "Subject")
    SubjectSubtitlePreset = apps.get_model("topics", "SubjectSubtitlePreset")
    presets = []
    seen = set()

    subjects = (
        Subject.objects.exclude(description="")
        .only("section_id", "description")
        .order_by("id")
    )
    for subject in subjects.iterator():
        value = (subject.description or "").strip()
        key = (subject.section_id, value.casefold())
        if not value or key in seen:
            continue
        seen.add(key)
        presets.append(
            SubjectSubtitlePreset(section_id=subject.section_id, value=value)
        )

    SubjectSubtitlePreset.objects.bulk_create(presets)


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0009_alter_subject_ordering"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubjectSubtitlePreset",
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
                ("value", models.CharField(max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(auto_now=True)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subtitle_presets",
                        to="topics.section",
                    ),
                ),
            ],
            options={
                "ordering": ["-last_used_at", "value"],
            },
        ),
        migrations.AddConstraint(
            model_name="subjectsubtitlepreset",
            constraint=models.UniqueConstraint(
                fields=("section", "value"),
                name="unique_subject_subtitle_per_section",
            ),
        ),
        migrations.RunPython(
            seed_subject_subtitle_presets,
            migrations.RunPython.noop,
        ),
    ]
