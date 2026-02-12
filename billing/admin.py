from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'student', 'course', 'amount', 'currency', 'provider', 'status', 'created_at']
    list_filter = ['status', 'provider', 'currency']
    search_fields = ['student__username', 'course__title', 'mpesa_receipt_number', 'paystack_reference']
    readonly_fields = ['transaction_id', 'paystack_reference', 'paystack_access_code',
                       'mpesa_checkout_request_id', 'mpesa_receipt_number']
    date_hierarchy = 'created_at'