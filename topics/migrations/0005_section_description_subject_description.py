from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0004_section_priority_section_weekly_goal_minutes_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="description",
            field=models.CharField(
                blank=True,
                help_text="Optional short description shown below the section name.",
                max_length=240,
            ),
        ),
        migrations.AddField(
            model_name="subject",
            name="description",
            field=models.CharField(
                blank=True,
                help_text="Optional short description shown below the subject name.",
                max_length=240,
            ),
        ),
    ]
