from .models import Topic


def sidebar_topics(request):

    if request.user.is_authenticated:

        topics = Topic.objects.filter(
            user=request.user
        ).prefetch_related("sections").order_by("-is_pinned", "title")

    else:

        topics = Topic.objects.none()

    return {

        "sidebar_topics": topics

    }
