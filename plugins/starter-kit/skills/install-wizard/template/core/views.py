from django.http import JsonResponse

from .models import Note


def health(request):
    """Liveness endpoint. Returns 200 as long as the database answers."""
    return JsonResponse({"ok": True, "notes": Note.objects.count()})
