import uuid
from django.db import models
from django.conf import settings
from courses.models import Course


class Payment(models.Model):
    PROVIDER_CHOICES = (
        ('paystack', 'Paystack (Card/M-Pesa)'),
        ('mpesa', 'M-Pesa Direct'),
        ('free', 'Free'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )
    CURRENCY_CHOICES = (
        ('KES', 'Kenyan Shilling'),
        ('USD', 'US Dollar'),
    )

    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='billing_payments'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='billing_payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='KES')
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')

    # Paystack
    paystack_reference = models.CharField(max_length=200, blank=True)
    paystack_access_code = models.CharField(max_length=200, blank=True)

    # M-Pesa direct
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    mpesa_phone = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.get_status_display()}"