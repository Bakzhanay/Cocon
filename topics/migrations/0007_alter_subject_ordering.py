from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0006_section_is_pinned_subject_is_pinned"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="subject",
            options={"ordering": ["completed", "-is_pinned", "title"]},
        ),
    ]
