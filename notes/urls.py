from django.urls import path
from . import views

app_name = "notes"

urlpatterns = [
    path("subject/<int:subject_id>/add/", views.add_subject_note, name="add_subject_note"),
    path("section/<int:section_id>/add/", views.add_section_note, name="add_section_note"),
    path("edit/<int:note_id>/", views.edit_note, name="edit_note"),
    path("delete/<int:note_id>/", views.delete_note, name="delete_note"),

    # Исправленные пути для удаления конкретных вложений
    path("pdf/delete/<int:pdf_id>/", views.delete_pdf, name="delete_pdf"),
    path("image/delete/<int:image_id>/", views.delete_image, name="delete_image"),

    path("section/<int:section_id>/", views.section_notes, name="section_notes"),
    path("<int:note_id>/pin/", views.toggle_pin, name="toggle_pin"),
    path("quick/", views.quick_notes, name="quick_notes"),
    path("quick/add/", views.add_quick_note, name="add_quick_note"),
    path("quick/<int:note_id>/pin/", views.toggle_quick_note_pin, name="toggle_quick_note_pin"),
    path("quick/<int:note_id>/delete/", views.delete_quick_note, name="delete_quick_note"),
    path("quick/<int:note_id>/undo-delete/", views.undo_delete_quick_note, name="undo_delete_quick_note"),
]
