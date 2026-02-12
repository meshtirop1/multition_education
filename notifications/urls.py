from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:pk>/read/', views.mark_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    # JSON API for dropdown polling
    path('api/', views.api_notifications, name='api_list'),
    path('api/<int:pk>/read/', views.api_mark_read, name='api_mark_read'),
]
