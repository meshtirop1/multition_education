from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EmailOTP, CookieConsent


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    readonly_fields = ('date_joined',)
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'status', 'email_verified']
    list_filter = ['role', 'status', 'email_verified', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        ('MultiTion Fields', {
            'fields': ('role', 'status', 'email_verified', 'cookie_consent', 'bio', 'phone', 'profile_picture'),
        }),
    )
    actions = ['approve_users', 'reject_users']

    def approve_users(self, request, queryset):
        queryset.update(status='approved')
    approve_users.short_description = "Approve selected users"

    def reject_users(self, request, queryset):
        queryset.update(status='rejected')
    reject_users.short_description = "Reject selected users"


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp', 'created_at', 'is_used', 'is_valid']
    list_filter = ['is_used']


@admin.register(CookieConsent)
class CookieConsentAdmin(admin.ModelAdmin):
    list_display = ['user', 'consented', 'consent_date']
