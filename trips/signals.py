import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """
    Every user (including ones made via createsuperuser) gets a Profile
    automatically, with a fresh email-verification token. The welcome email
    doubles as the verification email — one message, not two.
    """
    if created:
        profile, _ = Profile.objects.get_or_create(
            user=instance, defaults={'email_verification_token': secrets.token_urlsafe(24)}
        )
        if not profile.email_verification_token:
            profile.email_verification_token = secrets.token_urlsafe(24)
            profile.save(update_fields=['email_verification_token'])

        if instance.email:
            verify_path = reverse('verify-email', args=[profile.email_verification_token])
            verify_url = f"{settings.SITE_URL}{verify_path}"
            send_mail(
                subject='Welcome to Verbind — verify your email',
                message=(
                    f"Hi {instance.first_name or instance.username},\n\n"
                    "You're almost set. Before you can post or join a ride, verify "
                    f"your email by opening this link:\n\n{verify_url}\n\n"
                    "You'll also need to verify your identity from the Verify "
                    "Identity page — both are required before you can use Verbind."
                ),
                from_email=None,
                recipient_list=[instance.email],
                fail_silently=True,
            )
