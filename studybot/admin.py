from django.contrib import admin
from .models import ChatSession, ChatMessage


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'title', 'created_at', 'is_active']
    list_filter = ['is_active', 'course']
    search_fields = ['student__username', 'title']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'short_content', 'created_at']
    list_filter = ['role']

    def short_content(self, obj):
        return obj.content[:80]
    short_content.short_description = 'Content'
