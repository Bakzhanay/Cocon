import re

from django import forms
from .models import Topic, Section, Subject


_BULLET_RE = re.compile(
    r"^(?:[-*\u2022\u25e6\u25cb\u25aa\u2023\u203a]|\d+[.)])\s*(?P<text>\S.*)$"
)


def _strip_light_markdown(value):
    value = value.strip()
    if value.startswith("#"):
        value = value.lstrip("#").strip()
    for marker in ("**", "__", "`"):
        if value.startswith(marker) and value.endswith(marker) and len(value) > len(marker) * 2:
            value = value[len(marker):-len(marker)].strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    return value


def parse_bulk_subjects(raw_value):
    """Turn pasted outlines into ordered subject titles and subtitles."""
    lines = [
        (line_number, value.strip())
        for line_number, value in enumerate(raw_value.splitlines(), start=1)
        if value.strip()
    ]
    parsed = []
    current_subtitle = ""
    validation_errors = []

    for index, (line_number, raw_line) in enumerate(lines):
        bullet_match = _BULLET_RE.match(raw_line)
        next_is_bullet = (
            index + 1 < len(lines)
            and _BULLET_RE.match(lines[index + 1][1]) is not None
        )
        explicit_heading = (
            raw_line.endswith(":")
            or raw_line.startswith("#")
            or (raw_line.startswith("**") and raw_line.endswith("**"))
            or (raw_line.startswith("__") and raw_line.endswith("__"))
            or (raw_line.startswith("[") and raw_line.endswith("]"))
        )

        if "|" not in raw_line and (
            explicit_heading or (not bullet_match and next_is_bullet)
        ):
            current_subtitle = _strip_light_markdown(raw_line.rstrip(":"))
            if len(current_subtitle) > 240:
                validation_errors.append(
                    f"Line {line_number}: subtitle must be 240 characters or fewer."
                )
            continue

        item = bullet_match.group("text") if bullet_match else raw_line
        item = re.sub(r"^\[[ xX]\]\s*", "", item).strip()
        if "|" in item:
            title, subtitle = item.split("|", 1)
            subtitle = _strip_light_markdown(subtitle)
        else:
            title, subtitle = item, current_subtitle

        title = _strip_light_markdown(title)
        if not title:
            continue
        if len(title) > 100:
            validation_errors.append(
                f"Line {line_number}: subject name must be 100 characters or fewer."
            )
        if len(subtitle) > 240:
            validation_errors.append(
                f"Line {line_number}: subtitle must be 240 characters or fewer."
            )
        parsed.append({"title": title, "description": subtitle})

    if validation_errors:
        raise forms.ValidationError(validation_errors)
    return parsed


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
        fields = ["title", "description", "color", "weekly_goal_minutes", "priority"]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Subject name",
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example: The cell as the basis of life",
                    "maxlength": 240,
                    "list": "subjectSubtitleHistory",
                    "autocomplete": "off",
                }
            ),
            "color": forms.RadioSelect(),
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


class BulkSubjectForm(forms.Form):
    source_entries = forms.CharField(
        label="Paste subject names",
        strip=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control bulk-subject-source",
                "rows": 9,
                "placeholder": (
                    "Photosynthesis\n"
                    "Plant cells\n"
                    "Food chains"
                ),
                "autofocus": True,
            }
        ),
    )
    entries = forms.CharField(required=False, widget=forms.HiddenInput())
    preview_ready = forms.CharField(required=False, widget=forms.HiddenInput())
    common_subtitle = forms.CharField(
        label="Common subtitle",
        required=False,
        max_length=240,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Optional, for example: Biology basics",
                "list": "subjectSubtitleHistory",
                "autocomplete": "off",
            }
        ),
    )
    color = forms.ChoiceField(
        label="Card color",
        choices=Subject.COLOR_CHOICES,
        initial="default",
        widget=forms.RadioSelect(),
    )
    weekly_goal_minutes = forms.IntegerField(
        label="Weekly goal (minutes)",
        min_value=0,
        initial=120,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": 0, "step": 15}
        ),
    )
    priority = forms.ChoiceField(
        label="Priority",
        choices=Subject.PRIORITY_CHOICES,
        initial="normal",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("preview_ready") == "1":
            raw_entries = cleaned_data.get("entries", "")
        else:
            raw_entries = cleaned_data.get("source_entries", "")
        if not raw_entries:
            self.add_error("source_entries", "Add at least one subject name.")
            return cleaned_data

        try:
            parsed = parse_bulk_subjects(raw_entries)
        except forms.ValidationError as error:
            self.add_error("source_entries", error)
            return cleaned_data

        common_subtitle = (cleaned_data.get("common_subtitle") or "").strip()
        for entry in parsed:
            if not entry["description"]:
                entry["description"] = common_subtitle

        if not parsed:
            self.add_error("source_entries", "Add at least one subject name.")
        if len(parsed) > 200:
            self.add_error("source_entries", "You can add up to 200 subjects at a time.")
        cleaned_data["parsed_entries"] = parsed
        return cleaned_data
