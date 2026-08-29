from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

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


@login_required
@require_POST
def sync_timezone(request):
    timezone_name = request.POST.get("timezone", "").strip()
    if not timezone_name or len(timezone_name) > 64:
        return JsonResponse({"error": "Invalid timezone."}, status=400)

    try:
        ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        return JsonResponse({"error": "Unknown timezone."}, status=400)

    preferences_obj, _ = UserPreferences.objects.get_or_create(user=request.user)
    if not preferences_obj.auto_detect_timezone:
        return JsonResponse({
            "changed": False,
            "timezone": preferences_obj.timezone,
            "automatic": False,
        })

    changed = preferences_obj.timezone != timezone_name
    if changed:
        preferences_obj.timezone = timezone_name
        preferences_obj.save(update_fields=["timezone"])

    return JsonResponse({
        "changed": changed,
        "timezone": preferences_obj.timezone,
        "automatic": True,
    })
