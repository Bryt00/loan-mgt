from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.transactions.models import Wallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Automatically creates a Wallet instance whenever a new User is registered.
    """
    if created:
        Wallet.objects.create(
            user=instance,
            balance=0.00,
            currency="GHS"  # Adjust default currency as needed
        )