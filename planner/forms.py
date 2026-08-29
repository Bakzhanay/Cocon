from django import forms

from topics.models import Section, Subject, Topic

from .models import Milestone, Task


class TaskForm(forms.ModelForm):
    TASK_TYPE_CHOICES = [
        ("regular", "Regular task"),
        ("study", "Study plan"),
    ]

    task_type = forms.ChoiceField(
        choices=TASK_TYPE_CHOICES,
        initial="regular",
        required=False,
    )
    study_context = forms.ChoiceField(required=False)
    target_minutes = forms.IntegerField(required=False, min_value=5, max_value=1440)
    activity_type = forms.ChoiceField(
        choices=Task.ACTIVITY_CHOICES,
        required=False,
        initial="any",
    )

    class Meta:
        model = Task
        fields = (
            "title",
            "due_date",
            "priority",
            "target_minutes",
            "activity_type",
        )
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "What needs to be done?"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["title"].required = False
        choices = [("", "Choose what to study"), ("general", "General study")]
        if user and user.is_authenticated:
            topics = Topic.objects.filter(user=user).prefetch_related("sections__subjects")
            for topic in topics:
                choices.append((f"topic:{topic.id}", f"Topic · {topic.title}"))
                for section in topic.sections.all():
                    choices.append(
                        (f"section:{section.id}", f"Section · {topic.title} / {section.title}")
                    )
                    for subject in section.subjects.all():
                        choices.append(
                            (
                                f"subject:{subject.id}",
                                f"Subject · {topic.title} / {section.title} / {subject.title}",
                            )
                        )
        self.fields["study_context"].choices = choices
        self._study_target = (None, None)

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get("task_type") or "regular"
        title = (cleaned_data.get("title") or "").strip()

        if task_type == "regular":
            if not title:
                self.add_error("title", "Write what needs to be done.")
            cleaned_data["target_minutes"] = 0
            cleaned_data["activity_type"] = "any"
            return cleaned_data

        context_value = cleaned_data.get("study_context") or ""
        target_minutes = cleaned_data.get("target_minutes")
        if not context_value:
            self.add_error("study_context", "Choose a Topic, Section, or Subject.")
        if not target_minutes:
            self.add_error("target_minutes", "Choose how many minutes you plan to study.")

        kind = context_value
        target = None
        if context_value and context_value != "general":
            try:
                kind, raw_id = context_value.split(":", 1)
                target_id = int(raw_id)
            except (TypeError, ValueError):
                self.add_error("study_context", "Choose a valid study item.")
                return cleaned_data

            querysets = {
                "topic": Topic.objects.filter(user=self.user),
                "section": Section.objects.filter(topic__user=self.user),
                "subject": Subject.objects.filter(section__topic__user=self.user),
            }
            queryset = querysets.get(kind)
            target = queryset.filter(id=target_id).first() if queryset is not None else None
            if not target:
                self.add_error("study_context", "Choose a valid study item.")
                return cleaned_data

        self._study_target = (kind, target)
        if not title:
            context_label = target.title if target else "General study"
            activity = cleaned_data.get("activity_type") or "any"
            if activity == "flashcards":
                title = f"Review {context_label} flashcards"
            elif activity == "notes":
                title = f"Study {context_label} notes"
            else:
                title = f"Study {context_label}"
            cleaned_data["title"] = title[:220]
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.topic = None
        instance.section = None
        instance.subject = None

        if self.cleaned_data.get("task_type") == "study":
            kind, target = self._study_target
            if kind in {"topic", "section", "subject"}:
                setattr(instance, kind, target)
        else:
            instance.target_minutes = 0
            instance.focused_seconds = 0
            instance.activity_type = "any"
            instance.completed_by_focus = False

        if commit:
            instance.save()
        return instance


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ("kind", "title", "description", "target_at", "priority")
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Give this plan a clear title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Add details, steps, links, or anything you do not want to forget...",
                    "rows": 6,
                }
            ),
            "target_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_at"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ]

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Write the plan or deadline.")
        return title

    def clean_description(self):
        return self.cleaned_data.get("description", "").strip()

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("kind") == "deadline"
            and not cleaned_data.get("target_at")
        ):
            self.add_error(
                "target_at",
                "Choose the date and time for a deadline.",
            )
        return cleaned_data
