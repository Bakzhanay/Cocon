from django.urls import path
from . import views

app_name = "flashcards"

urlpatterns = [

    path(
        "due/",
        views.due_flashcards,
        name="due_flashcards",
    ),

    path(
        "section/<int:section_id>/",
        views.section_flashcards,
        name="section_flashcards",
    ),

    path(
        "section/<int:section_id>/add/",
        views.add_section_flashcard,
        name="add_section_flashcard",
    ),

    path(
        "edit/<int:flashcard_id>/",
        views.edit_flashcard,
        name="edit_flashcard",
    ),

    path(
        "delete/<int:flashcard_id>/",
        views.delete_flashcard,
        name="delete_flashcard",
    ),

    path(
        "image/delete/<int:flashcard_id>/",
        views.delete_question_image,
        name="delete_question_image",
    ),

    path(
        "subject/<int:subject_id>/",
        views.subject_flashcards,
        name="subject_flashcards",
    ),

    path(
        "subject/<int:subject_id>/add/",
        views.add_subject_flashcard,
        name="add_subject_flashcard",
    ),

    path(
        "toggle/<int:flashcard_id>/",
        views.toggle_flashcard,
        name="toggle_flashcard",
    ),

    path(
        "review/<int:flashcard_id>/",
        views.review_flashcard,
        name="review_flashcard",
    ),

    path(
        "subject/<int:subject_id>/shuffle/",
        views.shuffle_subject_flashcards,
        name="shuffle_subject_flashcards",
    ),

    path(
        "subject/<int:subject_id>/restore/",
        views.restore_subject_flashcards,
        name="restore_subject_flashcards",
    ),

]
