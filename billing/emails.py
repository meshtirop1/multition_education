from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings


def send_payment_receipt(payment):
    """Send payment receipt email to student."""
    context = {
        'payment': payment,
        'student': payment.student,
        'course': payment.course,
    }

    html_content = render_to_string('billing/email_receipt.html', context)

    email = EmailMessage(
        subject=f'Payment Receipt - {payment.course.title} | MultiTion Education',
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[payment.student.email],
    )
    email.content_subtype = 'html'
    email.send(fail_silently=True)