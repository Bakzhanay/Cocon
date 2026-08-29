from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0005_studysessionsegment"),
    ]

    operations = [
        migrations.AddField(
            model_name="studysession",
            name="entry_source",
            field=models.CharField(
                choices=[
                    ("timer", "Pomodoro timer"),
                    ("manual", "Manually logged"),
                ],
                default="timer",
                max_length=10,
            ),
        ),
    ]
