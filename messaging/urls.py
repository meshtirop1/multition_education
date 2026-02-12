from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('compose/', views.compose, name='compose'),
    path('<int:pk>/', views.conversation_detail, name='detail'),
    path('api/unread/', views.api_unread_count, name='api_unread'),
    path('api/<int:pk>/messages/', views.api_conversation_messages, name='api_messages'),
]
