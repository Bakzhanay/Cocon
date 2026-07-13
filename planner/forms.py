from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "due_date", "priority")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "What needs to be done?"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
