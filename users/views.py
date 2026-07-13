from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm, UserPreferencesForm
from .models import UserPreferences
# Create your views here.
def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect("topics:home")

    else:

        form = RegisterForm()

    return render(
        request,
        "registration/register.html",
        {
            "form": form
        }
    )


@login_required
def preferences(request):
    preferences_obj, _ = UserPreferences.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=preferences_obj)
        if form.is_valid():
            form.save()
            return redirect("topics:home")
    else:
        form = UserPreferencesForm(instance=preferences_obj)
    return render(request, "registration/preferences.html", {"form": form})
