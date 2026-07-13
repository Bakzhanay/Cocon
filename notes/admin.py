from django.contrib import admin
from .models import Note, NoteImage, NotePDF, QuickNote

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "section",
        "subject",
        "created_at",
    )
    search_fields = (
        "title",
        "content",
    )

admin.site.register(NoteImage)
admin.site.register(NotePDF)
admin.site.register(QuickNote)
