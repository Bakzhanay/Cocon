from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserPreferences


class RegisterForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email"
            }
        )
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):

        email = self.cleaned_data["email"]

        if User.objects.filter(email=email).exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_username(self):

        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():

            raise forms.ValidationError(
                "This username is already taken."
            )

        return username


class UserPreferencesForm(forms.ModelForm):
    timezone = forms.ChoiceField(
        choices=[
            ("UTC", "UTC"),
            ("Pacific/Honolulu", "Honolulu"),
            ("America/Los_Angeles", "Los Angeles / Vancouver"),
            ("America/Denver", "Denver"),
            ("America/Chicago", "Chicago"),
            ("America/New_York", "New York / Toronto"),
            ("America/Sao_Paulo", "São Paulo"),
            ("Europe/London", "London"),
            ("Europe/Paris", "Paris / Berlin"),
            ("Europe/Istanbul", "Istanbul"),
            ("Asia/Dubai", "Dubai"),
            ("Asia/Qyzylorda", "Qyzylorda"),
            ("Asia/Almaty", "Almaty"),
            ("Asia/Kolkata", "Delhi / Mumbai"),
            ("Asia/Bangkok", "Bangkok"),
            ("Asia/Singapore", "Singapore"),
            ("Asia/Tokyo", "Tokyo / Seoul"),
            ("Australia/Sydney", "Sydney"),
            ("Pacific/Auckland", "Auckland"),
        ],
    )

    class Meta:
        model = UserPreferences
        fields = ("daily_focus_goal_minutes", "weekly_focus_goal_minutes", "timezone")
        widgets = {
            "daily_focus_goal_minutes": forms.NumberInput(attrs={"min": 15, "step": 15}),
            "weekly_focus_goal_minutes": forms.NumberInput(attrs={"min": 30, "step": 30}),
        }
