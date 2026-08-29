import json
import re

from django import forms

from .models import Flashcard


FLASHCARD_LABEL_PATTERN = re.compile(
    r"^(?:\d+[.)]\s*)?"
    r"(?P<label>question|q|answer|a|notes?|n)\s*:\s*(?P<value>.*)$",
    re.IGNORECASE,
)


def parse_bulk_flashcards(raw_value):
    """Parse AI-friendly labelled flashcard blocks without truncating text."""
    cards = []
    current = {"question": "", "answer": "", "notes": ""}
    current_field = None

    def finish_card():
        nonlocal current, current_field
        if not any(value.strip() for value in current.values()):
            current = {"question": "", "answer": "", "notes": ""}
            current_field = None
            return

        number = len(cards) + 1
        question = current["question"].strip()
        answer = current["answer"].strip()
        notes = current["notes"].strip()
        errors = []
        if not question:
            errors.append(f"Card {number} needs a question.")
        if not answer:
            errors.append(f"Card {number} needs an answer.")
        if errors:
            raise forms.ValidationError(errors)
        cards.append({"question": question, "answer": answer, "notes": notes})
        current = {"question": "", "answer": "", "notes": ""}
        current_field = None

    normalized = (raw_value or "").replace("\r\n", "\n").replace("\r", "\n")
    for raw_line in normalized.split("\n"):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            continue
        if stripped == "---":
            finish_card()
            continue

        match = FLASHCARD_LABEL_PATTERN.match(stripped)
        if match:
            label = match.group("label").lower()
            field = {
                "question": "question",
                "q": "question",
                "answer": "answer",
                "a": "answer",
                "note": "notes",
                "notes": "notes",
                "n": "notes",
            }[label]
            if field == "question" and current["question"].strip():
                finish_card()
            current_field = field
            current[field] = match.group("value")
            continue

        if current_field is not None:
            existing = current[current_field]
            current[current_field] = f"{existing}\n{raw_line}" if existing else raw_line
        elif stripped:
            raise forms.ValidationError(
                "Start each card with 'Question:' and separate cards with '---'."
            )

    finish_card()
    return cards


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


class BulkFlashcardForm(forms.Form):
    source_entries = forms.CharField(
        label="Paste flashcards",
        strip=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control bulk-flashcard-source",
                "rows": 16,
                "placeholder": (
                    "Question: What is photosynthesis?\n"
                    "Answer: The process plants use to convert light into chemical energy.\n"
                    "Notes: Takes place mainly in chloroplasts.\n"
                    "---\n"
                    "Question: What pigment absorbs light?\n"
                    "Answer: Chlorophyll."
                ),
                "autofocus": True,
            }
        ),
    )
    entries = forms.CharField(required=False, widget=forms.HiddenInput())
    preview_ready = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        use_preview = cleaned_data.get("preview_ready") == "1"
        raw_value = (
            cleaned_data.get("entries", "")
            if use_preview
            else cleaned_data.get("source_entries", "")
        )
        if not raw_value:
            self.add_error("source_entries", "Add at least one flashcard.")
            return cleaned_data

        try:
            if use_preview:
                parsed = json.loads(raw_value)
                if not isinstance(parsed, list):
                    raise ValueError
                normalized = []
                for index, card in enumerate(parsed, start=1):
                    if not isinstance(card, dict):
                        raise ValueError
                    question = str(card.get("question", "")).strip()
                    answer = str(card.get("answer", "")).strip()
                    notes = str(card.get("notes", "")).strip()
                    errors = []
                    if not question:
                        errors.append(f"Card {index} needs a question.")
                    if not answer:
                        errors.append(f"Card {index} needs an answer.")
                    if errors:
                        raise forms.ValidationError(errors)
                    normalized.append({
                        "question": question,
                        "answer": answer,
                        "notes": notes,
                    })
                parsed = normalized
            else:
                parsed = parse_bulk_flashcards(raw_value)
        except (json.JSONDecodeError, TypeError, ValueError):
            self.add_error(
                "source_entries",
                "The preview data could not be read. Paste the cards again.",
            )
            return cleaned_data
        except forms.ValidationError as error:
            self.add_error("source_entries", error)
            return cleaned_data

        if not parsed:
            self.add_error("source_entries", "Add at least one flashcard.")
        elif len(parsed) > 200:
            self.add_error(
                "source_entries",
                "You can add up to 200 flashcards at a time.",
            )
        cleaned_data["parsed_entries"] = parsed
        return cleaned_data
