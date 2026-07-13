from django.contrib import admin

from .models import Flashcard


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("question_preview", "section", "subject", "learned", "next_review_at", "repetitions")
    list_filter = ("learned", "section", "subject")
    search_fields = ("question", "answer", "notes")

    @admin.display(description="Question")
    def question_preview(self, obj):
        return obj.question[:60]
