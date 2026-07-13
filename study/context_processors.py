def study_context(request):
    match = getattr(request, "resolver_match", None)
    app_name = getattr(match, "app_name", "") if match else ""
    url_name = getattr(match, "url_name", "") if match else ""

    if app_name == "flashcards":
        activity_type = "flashcards"
    elif app_name == "notes" or (app_name == "topics" and url_name == "subject_detail"):
        activity_type = "notes"
    else:
        activity_type = "general"

    return {"current_activity_type": activity_type}
