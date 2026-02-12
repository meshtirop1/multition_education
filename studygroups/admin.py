from django.contrib import admin
from .models import StudyGroup, Membership, GroupMessage


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'created_by', 'member_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'course']


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['student', 'group', 'role', 'is_active', 'joined_at']


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'group', 'content', 'created_at']