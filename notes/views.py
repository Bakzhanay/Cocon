from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.contrib.auth.decorators import login_required

# Импортируем новые модели для работы с множественными файлами
from .models import Note, NoteImage, NotePDF, QuickNote
from .forms import NoteForm

from topics.models import Subject, Section
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

@login_required
def add_subject_note(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        section__topic__user=request.user,
    )

    if request.method == "POST":
        form = NoteForm(request.POST)

        if form.is_valid():
            note = form.save(commit=False)
            note.owner = request.user
            note.subject = subject
            note.save()

            images = request.FILES.getlist('images')
            captions = request.POST.getlist('new_captions')

            for f, caption in zip(images, captions):
                NoteImage.objects.create(note=note, image=f, caption=caption.strip())

            # Обработка и сохранение массива PDF
            for f in request.FILES.getlist('pdfs'):
                NotePDF.objects.create(note=note, pdf=f)

            return redirect(
                "topics:subject_detail",
                subject_id=subject.id,
            )
    else:
        form = NoteForm()

    return render(
        request,
        "notes/add_note.html",
        {
            "form": form,
            "subject": subject,
        },
    )

@login_required
def add_section_note(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    if request.method == "POST":
        form = NoteForm(request.POST)

        if form.is_valid():
            note = form.save(commit=False)
            note.owner = request.user
            note.section = section
            note.save()

            images = request.FILES.getlist('images')
            captions = request.POST.getlist('new_captions')

            for f, caption in zip(images, captions):
                NoteImage.objects.create(note=note, image=f, caption=caption.strip())

            # Обработка и сохранение массива PDF
            for f in request.FILES.getlist('pdfs'):
                NotePDF.objects.create(note=note, pdf=f)

            return redirect(
                "topics:section_detail",
                section_id=section.id,
            )
    else:
        form = NoteForm()

    return render(
        request,
        "notes/add_note.html",
        {
            "form": form,
            "section": section,
        },
    )

@login_required
def section_notes(request, section_id):
    section = get_object_or_404(
        Section,
        id=section_id,
        topic__user=request.user,
    )

    return redirect("topics:section_detail", section_id=section.id)

@login_required
def edit_note(request, note_id):
    note = get_object_or_404(
        Note,
        id=note_id,
        owner=request.user,
    )

    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)

        if form.is_valid():
            note = form.save(commit=False)
            note.save()

            # 1. Обновление подписей уже СУЩЕСТВУЮЩИХ картинок
            for img_obj in note.images.all():
                caption_value = request.POST.get(f'caption_{img_obj.id}', '').strip()
                if img_obj.caption != caption_value:
                    img_obj.caption = caption_value
                    img_obj.save()

            # 2. Сохранение НОВЫХ картинок с их подписями
            new_images = request.FILES.getlist('images')
            new_captions = request.POST.getlist('new_captions')

            for f, caption in zip(new_images, new_captions):
                NoteImage.objects.create(note=note, image=f, caption=caption.strip())

            # Позволяет догружать новые PDF при редактировании
            for f in request.FILES.getlist('pdfs'):
                NotePDF.objects.create(note=note, pdf=f)

            if note.section:
                return redirect(
                    "topics:section_detail",
                    section_id=note.section.id,
                )

            return redirect(
                "topics:subject_detail",
                subject_id=note.subject.id,
            )
    else:
        form = NoteForm(instance=note)

    return render(
        request,
        "notes/edit_note.html",
        {
            "form": form,
            "note": note,
        },
    )

@login_required
def delete_note(request, note_id):
    note = get_object_or_404(
        Note,
        id=note_id,
        owner=request.user,
    )

    if request.method == "POST":
        section = note.section
        subject = note.subject

        note.delete()

        if section:
            return redirect(
                "topics:section_detail",
                section_id=section.id,
            )

        return redirect(
            "topics:subject_detail",
            subject_id=subject.id,
        )

    return render(
        request,
        "notes/delete_note.html",
        {
            "note": note,
        },
    )


@login_required
def delete_pdf(request, pdf_id):
    # Ищем конкретный объект PDF, проверяя, что заметка принадлежит текущему пользователю
    pdf_obj = get_object_or_404(
        NotePDF,
        id=pdf_id,
        note__owner=request.user
    )
    # Запоминаем ID заметки, чтобы вернуться к её редактированию
    parent_note_id = pdf_obj.note.id

    if request.method == "POST":
        if pdf_obj.pdf:
            pdf_obj.pdf.delete(save=False) # Удаление файла из файловой системы
        pdf_obj.delete()                   # Удаление записи из БД

        return redirect(
            "notes:edit_note",
            note_id=parent_note_id,
        )

    return render(
        request,
        "notes/delete_pdf.html",
        {
            "pdf_obj": pdf_obj,
        },
    )

@login_required
def delete_image(request, image_id):
    # Ищем конкретный объект картинки
    image_obj = get_object_or_404(
        NoteImage,
        id=image_id,
        note__owner=request.user
    )
    parent_note_id = image_obj.note.id

    if request.method == "POST":
        if image_obj.image:
            image_obj.image.delete(save=False) # Удаление файла
        image_obj.delete()                     # Удаление записи

        return redirect(
            "notes:edit_note",
            note_id=parent_note_id,
        )

    return render(
        request,
        "notes/delete_image.html",
        {
            "image_obj": image_obj,
        },
    )


@login_required
@require_POST
def toggle_pin(request, note_id):
    note = get_object_or_404(Note, id=note_id, owner=request.user)
    note.is_pinned = not note.is_pinned
    note.save(update_fields=["is_pinned"])
    if note.subject_id:
        return redirect("topics:subject_detail", subject_id=note.subject_id)
    return redirect("topics:section_detail", section_id=note.section_id)


@login_required
@require_POST
def add_quick_note(request):
    content = request.POST.get("content", "").strip()
    if content:
        QuickNote.objects.create(owner=request.user, content=content[:1000])
    return _quick_note_redirect(request)


def _quick_note_redirect(request):
    if request.POST.get("source") == "dashboard":
        return redirect("topics:home")
    return redirect("notes:quick_notes")


@login_required
def quick_notes(request):
    deleted_quick_note = None
    deleted_note_id = request.GET.get("quick_note_deleted", "")
    if deleted_note_id.isdigit():
        deleted_quick_note = QuickNote.objects.filter(
            id=int(deleted_note_id),
            owner=request.user,
            deleted_at__isnull=False,
        ).first()
    return render(request, "notes/quick_notes.html", {
        "quick_notes": QuickNote.objects.filter(
            owner=request.user,
            deleted_at__isnull=True,
        ),
        "deleted_quick_note": deleted_quick_note,
    })


@login_required
@require_POST
def toggle_quick_note_pin(request, note_id):
    quick_note = get_object_or_404(
        QuickNote,
        id=note_id,
        owner=request.user,
        deleted_at__isnull=True,
    )
    quick_note.is_pinned = not quick_note.is_pinned
    quick_note.save(update_fields=["is_pinned", "updated_at"])
    return _quick_note_redirect(request)


@login_required
@require_POST
def delete_quick_note(request, note_id):
    quick_note = get_object_or_404(
        QuickNote,
        id=note_id,
        owner=request.user,
        deleted_at__isnull=True,
    )
    quick_note.deleted_at = timezone.now()
    quick_note.save(update_fields=["deleted_at"])
    target = reverse("notes:quick_notes")
    return redirect(f"{target}?quick_note_deleted={quick_note.id}")


@login_required
@require_POST
def undo_delete_quick_note(request, note_id):
    quick_note = get_object_or_404(
        QuickNote,
        id=note_id,
        owner=request.user,
        deleted_at__isnull=False,
    )
    quick_note.deleted_at = None
    quick_note.save(update_fields=["deleted_at"])
    return _quick_note_redirect(request)
