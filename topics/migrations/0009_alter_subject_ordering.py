from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0008_subject_color"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="subject",
            options={
                "ordering": ["completed", "-is_pinned", "created_at", "id"],
            },
        ),
    ]
