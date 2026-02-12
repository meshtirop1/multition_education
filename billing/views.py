import json
import requests
import base64
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

from courses.models import Course, Enrollment
from notifications.utils import create_notification
from .models import Payment
from .emails import send_payment_receipt


# ===================== CHECKOUT PAGE =====================

@login_required
def checkout(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)

    if not request.user.is_approved:
        messages.warning(request, 'Your account must be approved before purchasing.')
        return redirect('courses:detail', slug=slug)

    if Enrollment.objects.filter(student=request.user, course=course, is_active=True).exists():
        messages.info(request, 'You are already enrolled in this course.')
        return redirect('courses:detail', slug=slug)

    # Free course
    if course.is_free or course.price <= 0:
        Enrollment.objects.get_or_create(
            student=request.user, course=course,
            defaults={'status': 'enrolled'}
        )
        Payment.objects.create(
            student=request.user, course=course,
            amount=0, provider='free', status='completed',
            completed_at=timezone.now()
        )
        messages.success(request, f'Enrolled in {course.title} for free!')
        return redirect('courses:detail', slug=slug)

    kes_price = course.price_kes if course.price_kes > 0 else course.price * Decimal('150')

    context = {
        'course': course,
        'kes_price': kes_price,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'billing/checkout.html', context)


# ===================== PAYSTACK =====================

@login_required
@require_POST
def paystack_initialize(request, slug):
    """Initialize Paystack transaction."""
    course = get_object_or_404(Course, slug=slug)

    kes_price = course.price_kes if course.price_kes > 0 else course.price * Decimal('150')

    payment = Payment.objects.create(
        student=request.user,
        course=course,
        amount=kes_price,
        currency='KES',
        provider='paystack',
    )

    # Paystack expects amount in cents (kobo/cents)
    amount_in_cents = int(kes_price * 100)

    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }

    payload = {
        'email': request.user.email,
        'amount': amount_in_cents,
        'currency': 'KES',
        'reference': str(payment.transaction_id),
        'callback_url': request.build_absolute_uri(f'/billing/paystack/callback/'),
        'metadata': {
            'payment_id': str(payment.transaction_id),
            'course_id': course.id,
            'student_id': request.user.id,
            'course_title': course.title,
        },
        'channels': ['card', 'mobile_money'],
    }

    try:
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json=payload, headers=headers
        )
        data = response.json()

        if data.get('status'):
            payment.paystack_reference = data['data']['reference']
            payment.paystack_access_code = data['data']['access_code']
            payment.save()
            return redirect(data['data']['authorization_url'])
        else:
            payment.status = 'failed'
            payment.save()
            messages.error(request, data.get('message', 'Payment initialization failed.'))
            return redirect('billing:checkout', slug=slug)

    except Exception as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, 'Payment service unavailable. Try again later.')
        return redirect('billing:checkout', slug=slug)


@login_required
def paystack_callback(request):
    """Handle Paystack redirect after payment."""
    reference = request.GET.get('reference', '')

    if not reference:
        messages.error(request, 'Invalid payment reference.')
        return redirect('courses:list')

    # Verify with Paystack
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
    }

    try:
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers
        )
        data = response.json()

        payment = Payment.objects.filter(paystack_reference=reference).first()
        if not payment:
            payment = Payment.objects.filter(transaction_id=reference).first()

        if not payment:
            messages.error(request, 'Payment not found.')
            return redirect('courses:list')

        if data.get('status') and data['data']['status'] == 'success':
            if payment.status != 'completed':
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()
                _enroll_after_payment(payment)

            return render(request, 'billing/payment_success.html', {
                'payment': payment, 'course': payment.course
            })
        else:
            payment.status = 'failed'
            payment.save()
            return render(request, 'billing/payment_cancel.html', {
                'payment': payment, 'course': payment.course
            })

    except Exception:
        messages.error(request, 'Could not verify payment. Contact support.')
        return redirect('courses:list')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook events."""
    # Verify webhook signature
    paystack_signature = request.headers.get('X-Paystack-Signature', '')
    import hashlib
    import hmac
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        request.body,
        hashlib.sha512
    ).hexdigest()

    if paystack_signature != expected:
        return HttpResponse(status=400)

    try:
        data = json.loads(request.body)
        event = data.get('event')

        if event == 'charge.success':
            reference = data['data']['reference']
            payment = Payment.objects.filter(paystack_reference=reference).first()
            if not payment:
                payment = Payment.objects.filter(transaction_id=reference).first()

            if payment and payment.status != 'completed':
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()
                _enroll_after_payment(payment)

    except Exception:
        pass

    return HttpResponse(status=200)


# ===================== M-PESA DIRECT (Daraja API) =====================

def _get_mpesa_access_token():
    url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(
        settings.MPESA_CONSUMER_KEY,
        settings.MPESA_CONSUMER_SECRET
    ))
    return response.json().get('access_token')


def _generate_mpesa_password():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    data = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    encoded = base64.b64encode(data.encode()).decode('utf-8')
    return encoded, timestamp


@login_required
@require_POST
def mpesa_stk_push(request, slug):
    course = get_object_or_404(Course, slug=slug)
    phone = request.POST.get('phone', '').strip()

    if not phone:
        return JsonResponse({'error': 'Phone number is required'}, status=400)

    phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone

    kes_price = course.price_kes if course.price_kes > 0 else int(course.price * Decimal('150'))

    payment = Payment.objects.create(
        student=request.user,
        course=course,
        amount=kes_price,
        currency='KES',
        provider='mpesa',
        mpesa_phone=phone,
    )

    try:
        access_token = _get_mpesa_access_token()
        password, timestamp = _generate_mpesa_password()

        url = f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
        headers = {'Authorization': f'Bearer {access_token}'}

        payload = {
            'BusinessShortCode': settings.MPESA_SHORTCODE,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(kes_price),
            'PartyA': phone,
            'PartyB': settings.MPESA_SHORTCODE,
            'PhoneNumber': phone,
            'CallBackURL': request.build_absolute_uri('/billing/mpesa/callback/'),
            'AccountReference': f'MultiTion-{course.id}',
            'TransactionDesc': f'Payment for {course.title[:20]}',
        }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if data.get('ResponseCode') == '0':
            payment.mpesa_checkout_request_id = data['CheckoutRequestID']
            payment.save()
            return JsonResponse({
                'status': 'ok',
                'message': 'Check your phone and enter your M-Pesa PIN.',
                'checkout_request_id': data['CheckoutRequestID'],
                'payment_id': str(payment.transaction_id),
            })
        else:
            payment.status = 'failed'
            payment.save()
            return JsonResponse({
                'status': 'error',
                'message': data.get('errorMessage', 'Failed to initiate payment.'),
            }, status=400)

    except Exception:
        payment.status = 'failed'
        payment.save()
        return JsonResponse({
            'status': 'error',
            'message': 'Payment service unavailable.',
        }, status=500)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    try:
        data = json.loads(request.body)
        callback = data.get('Body', {}).get('stkCallback', {})
        checkout_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')

        payment = Payment.objects.filter(mpesa_checkout_request_id=checkout_id).first()
        if not payment:
            return HttpResponse(status=200)

        if result_code == 0:
            items = callback.get('CallbackMetadata', {}).get('Item', [])
            receipt = ''
            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    receipt = item.get('Value', '')

            payment.status = 'completed'
            payment.mpesa_receipt_number = receipt
            payment.completed_at = timezone.now()
            payment.save()
            _enroll_after_payment(payment)
        else:
            payment.status = 'failed'
            payment.save()
    except Exception:
        pass

    return HttpResponse(status=200)


@login_required
def mpesa_check_status(request, payment_id):
    payment = get_object_or_404(Payment, transaction_id=payment_id, student=request.user)
    return JsonResponse({
        'status': payment.status,
        'completed': payment.status == 'completed',
    })


# ===================== SHARED =====================

def _enroll_after_payment(payment):
    enrollment, created = Enrollment.objects.get_or_create(
        student=payment.student,
        course=payment.course,
        defaults={'status': 'enrolled'}
    )

    if created:
        create_notification(
            recipient=payment.student,
            title='Payment Successful!',
            message=f'You are now enrolled in "{payment.course.title}". Start learning!',
            notification_type='success',
            link=f'/courses/{payment.course.slug}/'
        )
        if payment.course.mentor:
            create_notification(
                recipient=payment.course.mentor,
                title='New Paid Enrollment',
                message=f'{payment.student.username} purchased and enrolled in {payment.course.title}.',
                notification_type='info',
                link=f'/dashboard/mentor/course/{payment.course.slug}/'
            )
        send_payment_receipt(payment)


@login_required
def payment_history(request):
    payments = Payment.objects.filter(student=request.user).select_related('course')
    return render(request, 'billing/payment_history.html', {'payments': payments})