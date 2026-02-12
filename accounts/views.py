from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import CustomUser, EmailOTP, CookieConsent
from .forms import (
    StudentRegistrationForm, LoginForm, OTPVerificationForm,
    UserProfileForm, MentorCreationForm
)
from notifications.utils import create_notification


def register_student(request):
    """Student registration view."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Generate and send OTP
            otp = EmailOTP.objects.create(user=user)
            send_mail(
                'MultiTion Education - Verify Your Email',
                f'Your verification code is: {otp.otp}\n\nThis code expires in 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            request.session['verify_user_id'] = user.pk
            messages.success(request, 'Registration successful! Please verify your email.')
            return redirect('accounts:verify_otp')
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_otp(request):
    """Email OTP verification view."""
    user_id = request.session.get('verify_user_id')
    if not user_id:
        messages.error(request, 'Please register first.')
        return redirect('accounts:register')

    user = get_object_or_404(CustomUser, pk=user_id)

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp']
            otp_obj = EmailOTP.objects.filter(
                user=user, otp=otp_code, is_used=False
            ).first()

            if otp_obj and otp_obj.is_valid:
                otp_obj.is_used = True
                otp_obj.save()
                user.email_verified = True
                user.save()
                del request.session['verify_user_id']

                # Notify admins about new registration
                admins = CustomUser.objects.filter(role='admin', is_active=True)
                for admin_user in admins:
                    create_notification(
                        recipient=admin_user,
                        title='New Student Registration',
                        message=f'{user.get_full_name() or user.username} has registered and is awaiting approval.',
                        notification_type='info',
                        link='/dashboard/admin/students/'
                    )

                create_notification(
                    recipient=user,
                    title='Welcome to MultiTion Education!',
                    message='Your email has been verified. Please wait for admin approval to access courses.',
                    notification_type='success'
                )

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Email verified! Your account is pending admin approval.')
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid or expired OTP. Please try again.')
    else:
        form = OTPVerificationForm()

    return render(request, 'accounts/verify_otp.html', {
        'form': form,
        'email': user.email,
    })


def resend_otp(request):
    """Resend OTP."""
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return JsonResponse({'error': 'No pending verification'}, status=400)

    user = get_object_or_404(CustomUser, pk=user_id)
    # Invalidate old OTPs
    EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)
    # Create new OTP
    otp = EmailOTP.objects.create(user=user)
    send_mail(
        'MultiTion Education - New Verification Code',
        f'Your new verification code is: {otp.otp}\n\nThis code expires in 10 minutes.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
    return JsonResponse({'message': 'New OTP sent to your email.'})


def login_view(request):
    """Custom login view."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email_verified and user.role == 'student':
                request.session['verify_user_id'] = user.pk
                otp = EmailOTP.objects.create(user=user)
                send_mail(
                    'MultiTion Education - Verify Your Email',
                    f'Your verification code is: {otp.otp}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
                messages.info(request, 'Please verify your email first.')
                return redirect('accounts:verify_otp')
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard:home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


@login_required
def profile_view(request):
    """User profile view."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@require_POST
def cookie_consent_view(request):
    """Handle cookie consent."""
    import json
    try:
        data = json.loads(request.body)
        consented = data.get('consent', False)
    except (json.JSONDecodeError, ValueError):
        consented = request.POST.get('consent') == 'true'
    if request.user.is_authenticated:
        CookieConsent.objects.update_or_create(
            user=request.user,
            defaults={
                'consented': consented,
                'ip_address': request.META.get('REMOTE_ADDR'),
            }
        )
        request.user.cookie_consent = consented
        request.user.save()
    else:
        CookieConsent.objects.create(
            session_key=request.session.session_key or 'anonymous',
            consented=consented,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    request.session['cookie_consent'] = consented
    return JsonResponse({'status': 'ok'})
