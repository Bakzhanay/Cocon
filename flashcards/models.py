from django.db import models

from topics.models import Section, Subject
# Create your models here.
class Flashcard(models.Model):

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="flashcards",
        null=True,
        blank=True,
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="flashcards",
        null=True,
        blank=True,
    )

    question = models.TextField()

    question_image = models.ImageField(
        upload_to="flashcards/questions/",
        blank=True,
        null=True,
    )

    answer = models.TextField()

    answer_image = models.ImageField(
        upload_to="flashcards/answers/",
        blank=True,
        null=True,
    )

    notes = models.TextField(blank=True)

    learned = models.BooleanField(
    default=False,
    )

    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    next_review_at = models.DateTimeField(null=True, blank=True, db_index=True)

    interval_days = models.PositiveIntegerField(default=0)

    repetitions = models.PositiveIntegerField(default=0)

    ease_factor = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=2.50,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(section__isnull=False, subject__isnull=True)
                    | models.Q(section__isnull=True, subject__isnull=False)
                ),
                name="flashcard_has_exactly_one_context",
            ),
        ]

    def __str__(self):
        return self.question[:50]
