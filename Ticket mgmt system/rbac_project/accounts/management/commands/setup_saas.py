import os
from django.core.management.base import BaseCommand
from accounts.models import SubscriptionPlan, Company, Subscription
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Populates subscription plans and fixes missing subscriptions for existing companies.'

    def handle(self, *args, **options):
        # 1. Create Plans
        plans_data = [
            {'name': 'Free Trial', 'duration_days': 30},
            {'name': 'Basic', 'duration_days': 30},
            {'name': 'Professional', 'duration_days': 365},
            {'name': 'Enterprise', 'duration_days': 9999},
        ]

        self.stdout.write(self.style.SUCCESS('--- Populating Subscription Plans ---'))
        for data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=data['name'],
                defaults={'duration_days': data['duration_days']}
            )
            if created:
                self.stdout.write(f'Created plan: {plan.name}')
            else:
                self.stdout.write(f'Plan already exists: {plan.name}')

        # 2. Fix Existing Companies
        self.stdout.write(self.style.SUCCESS('\n--- Repairing Missing Subscriptions ---'))
        free_trial_plan = SubscriptionPlan.objects.get(name='Free Trial')
        
        companies_without_sub = Company.objects.filter(subscriptions__isnull=True)
        count = companies_without_sub.count()
        
        if count == 0:
            self.stdout.write('No companies found without subscriptions.')
        else:
            for company in companies_without_sub:
                Subscription.objects.create(
                    company=company,
                    plan=free_trial_plan,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=free_trial_plan.duration_days),
                    is_active=True
                )
                self.stdout.write(f'Assigned Free Trial to: {company.name}')
            
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully repaired {count} companies.'))

        self.stdout.write(self.style.SUCCESS('\n--- Initialization Complete ---'))
