from django import forms
from .models import Flashcard


class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = [
            "question",
            "question_image",
            "answer",
            "answer_image",
            "notes",
        ]

        widgets = {
            "question": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Question",
                }
            ),
            "answer": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Answer",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Notes (optional)",
                }
            ),
        }