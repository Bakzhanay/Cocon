from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0005_section_description_subject_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="subject",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name="section",
            options={"ordering": ["-is_pinned", "title"]},
        ),
        migrations.AlterModelOptions(
            name="subject",
            options={"ordering": ["-is_pinned", "title"]},
        ),
    ]
