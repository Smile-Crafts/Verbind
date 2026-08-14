from django.db.models import Q

from .models import Message


def unread_messages(request):
    """Makes the unread-message count available in base.html's navbar on
    every page, without every view having to compute and pass it."""
    if not request.user.is_authenticated:
        return {}
    count = Message.objects.filter(recipient=request.user, read=False).count()
    return {'unread_message_count': count}
