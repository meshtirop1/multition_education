from .models import Notification


def create_notification(recipient, title, message, notification_type='info', link=None):
    """Create a notification for a user."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )
