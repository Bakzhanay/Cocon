from django.db import migrations, models


def clear_mastered_review_dates(apps, schema_editor):
    Flashcard = apps.get_model("flashcards", "Flashcard")
    Flashcard.objects.filter(learned=True).update(next_review_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ("flashcards", "0005_flashcard_ease_factor_flashcard_interval_days_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="flashcard",
            name="review_state",
            field=models.CharField(
                blank=True,
                choices=[
                    ("again", "Again"),
                    ("hard", "Hard"),
                    ("good", "Good"),
                    ("easy", "Easy"),
                ],
                default="",
                max_length=5,
            ),
        ),
        migrations.RunPython(clear_mastered_review_dates, migrations.RunPython.noop),
    ]
