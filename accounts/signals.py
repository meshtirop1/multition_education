from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added, pre_social_login


@receiver(user_signed_up)
def social_user_signed_up(sender, request, user, **kwargs):
    """Auto-approve and verify social auth users."""
    if hasattr(user, 'socialaccount_set') and user.socialaccount_set.exists():
        user.status = 'approved'
        user.email_verified = True
        user.save()


@receiver(social_account_added)
def social_account_was_added(sender, request, sociallogin, **kwargs):
    """When a social account is linked, approve the user."""
    user = sociallogin.user
    user.status = 'approved'
    user.email_verified = True
    user.save()


@receiver(pre_social_login)
def pre_social_login_handler(sender, request, sociallogin, **kwargs):
    """Auto-approve returning social auth users."""
    request._sociallogin = sociallogin
    user = sociallogin.user
    if user.pk and user.status != 'approved':
        user.status = 'approved'
        user.email_verified = True
        user.save()
