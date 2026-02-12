from django.contrib import admin
from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'certificate_id', 'issued_at', 'approved_by']
    list_filter = ['course', 'issued_at']
    search_fields = ['student__username', 'course__title', 'certificate_id']
    readonly_fields = ['certificate_id']
