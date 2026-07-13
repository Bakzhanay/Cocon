import os
import uuid

from django.db import models
from django.contrib.auth.models import User
from topics.models import Section, Subject

class Note(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="notes")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name="notes")
    title = models.CharField(max_length=200)
    references = models.TextField(blank=True)
    reference_title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(section__isnull=False, subject__isnull=True)
                    | models.Q(section__isnull=True, subject__isnull=False)
                ),
                name="note_has_exactly_one_context",
            ),
        ]

    def __str__(self):
        return self.title

def get_image_upload_path(instance, filename):
    # Извлекаем расширение (например, '.jpg' или '.png')
    ext = os.path.splitext(filename)[1].lower()

    # Если имя было ".jpg" (без названия), splitext запишет его в base, а ext будет пустым. Исправляем:
    if not ext and filename.startswith('.'):
        ext = filename.lower()

    # Страховка: если расширения вообще нет, принудительно ставим .jpg
    if not ext:
        ext = '.jpg'

    # Генерируем случайное уникальное имя, к которому приклеиваем расширение в конец
    unique_filename = f"{uuid.uuid4().hex[:10]}{ext}"

    # Возвращаем полный путь внутри папки медиа
    return os.path.join('notes/images/', unique_filename)

class NoteImage(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="images")

    # ИЗМЕНЕНО: теперь вместо строки используется функция очистки имени
    image = models.ImageField(upload_to=get_image_upload_path)

    caption = models.CharField(max_length=250, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class NotePDF(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="pdfs")
    pdf = models.FileField(upload_to="notes/pdfs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class QuickNote(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quick_notes")
    content = models.TextField(max_length=1000)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]

    def __str__(self):
        return self.content[:60]
