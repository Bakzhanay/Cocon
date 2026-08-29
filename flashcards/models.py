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

    REVIEW_STATE_CHOICES = [
        ("again", "Again"),
        ("hard", "Hard"),
        ("good", "Good"),
        ("easy", "Easy"),
    ]

    # The manual checkbox still controls whether a card is mastered.  This
    # separate value records the latest review result while the card remains
    # in the learning queue, so a learner can see which cards feel easy or
    # difficult without conflating review progress with mastery.
    review_state = models.CharField(
        max_length=5,
        choices=REVIEW_STATE_CHOICES,
        blank=True,
        default="",
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

    @property
    def hard_interval_label(self):
        if not self.interval_days:
            return "10m"
        return f"{max(1, round(self.interval_days * 1.2))}d+"

    @property
    def good_interval_label(self):
        if not self.interval_days:
            return "1d+"
        if self.interval_days == 1 and self.repetitions <= 2:
            return "3d+"
        return f"{max(1, round(self.interval_days * float(self.ease_factor)))}d+"

    @property
    def easy_interval_label(self):
        if not self.interval_days:
            return "3d+"
        return f"{max(1, round(self.interval_days * float(self.ease_factor) * 1.3))}d+"

    @property
    def review_schedule_label(self):
        """Return a calm, current label instead of a stale past date."""
        if self.learned or not self.next_review_at:
            return ""
        from django.utils import timezone

        if self.next_review_at <= timezone.now():
            return "Review due"
        local_review = timezone.localtime(self.next_review_at)
        return f"Next {local_review.strftime('%b')} {local_review.day}"

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
