from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0007_alter_subject_ordering"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="color",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("sage", "Sage"),
                    ("sky", "Sky blue"),
                    ("lavender", "Lavender"),
                    ("rose", "Rose"),
                    ("peach", "Peach"),
                    ("butter", "Soft yellow"),
                    ("mint", "Mint"),
                ],
                default="default",
                max_length=12,
            ),
        ),
    ]
