from django.urls import path
from . import api_views

urlpatterns = [
    path('notifications/', api_views.api_notifications, name='api-notifications'),
    path('notifications/<int:pk>/read/', api_views.api_mark_read, name='api-notif-read'),
    path('notifications/mark-all-read/', api_views.api_mark_all_read, name='api-notif-mark-all'),
]
