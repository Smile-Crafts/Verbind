from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Every user (including ones made via createsuperuser) gets a Profile automatically."""
    if created:
        Profile.objects.get_or_create(user=instance)
        if instance.email:
            send_mail(
                subject='Welcome to Verbind',
                message=(
                    f"Hi {instance.username},\n\n"
                    "You're all set. Complete your profile, then browse or post "
                    "a ride to get started."
                ),
                from_email=None,
                recipient_list=[instance.email],
                fail_silently=True,
            )
