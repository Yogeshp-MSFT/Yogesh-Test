from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Company, Subscription, SubscriptionPlan

@receiver(post_save, sender=Company)
def create_company_subscription(sender, instance, created, **kwargs):
    if created:
        # Ensure a default plan exists
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name="Free Trial",
            defaults={'duration_days': 30}
        )
        
        # Create Subscription
        Subscription.objects.create(
            company=instance,
            plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=plan.duration_days),
            is_active=True
        )
