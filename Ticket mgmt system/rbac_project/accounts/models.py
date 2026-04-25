from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    is_self_registered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Department model for dynamic department management.
    Admins can add/edit departments from Django admin panel.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class User(AbstractUser):

    ROLE_CHOICES = (
        ('COMPANY_ADMIN', 'Company Admin'),
        ('MANAGER', 'Manager'),
        ('EDITOR', 'Editor'),
        ('VIEWER', 'Employee'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='VIEWER')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    contact = models.CharField(max_length=50, blank=True, null=True)
    whatsapp_available = models.BooleanField(default=False)
    # mark whether this user was created via the admin/create-user view
    created_by_admin = models.BooleanField(default=False)
    # flag for the primary administrator of a company tenant
    is_company_admin = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            # Enforce single SuperAdmin rule
            existing_superadmin = User.objects.filter(is_superuser=True).exclude(id=self.id)
            if existing_superadmin.exists():
                raise ValueError("There can be only one SuperAdmin in the system.")
        
        # Enforce Single Manager/Editor per Company rule
        if self.company and self.role in ['MANAGER', 'EDITOR']:
            # Automatically demote any existing Manager/Editor in the same company to VIEWER
            User.objects.filter(company=self.company, role=self.role).exclude(id=self.id).update(role='VIEWER')
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.role}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, default="Free Trial")
    duration_days = models.IntegerField(default=30)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"

    @property
    def days_remaining(self):
        if not self.end_date:
            return 0
        delta = self.end_date - timezone.now()
        return max(0, delta.days)

