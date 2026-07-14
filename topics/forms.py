from django import forms
from .models import Topic, Section, Subject


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["title", "weekly_goal_minutes", "priority"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Topic name"
                }
            ),
            "weekly_goal_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 15}
            ),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ["title", "description", "weekly_goal_minutes", "priority"]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Section name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "What belongs in this section?",
                    "rows": 2,
                    "maxlength": 240,
                }
            ),
            "weekly_goal_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 15}
            ),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["title", "description", "weekly_goal_minutes", "priority"]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Subject name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example: The cell as the basis of life",
                    "rows": 2,
                    "maxlength": 240,
                }
            ),
            "weekly_goal_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": 15,
                    "placeholder": "120",
                }
            ),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }
