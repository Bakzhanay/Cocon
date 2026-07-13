from django import forms
from .models import Note

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = [
            "title",
            "reference_title",
            "references",
            "content",
        ]
        widgets = {
            "references": forms.URLInput(attrs={"placeholder": "https://..."}),
            "content": forms.Textarea(attrs={"rows": 10}),
        }