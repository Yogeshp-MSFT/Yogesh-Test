from django.db import models
from django.utils import timezone
from accounts.models import User, Department, Company

class Ticket(models.Model):
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MID', 'Mid'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    )

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assigned_to_me')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_created_by_me')
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MID')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    project_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'

    def __str__(self):
        return f"Ticket #{self.id} - {self.title}"


class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_attachments')

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'

    def __str__(self):
        return f"Attachment for Ticket #{self.ticket.id}"


class ActivityTimeline(models.Model):
    ACTIVITY_TYPES = (
        ('STATUS_CHANGE', 'Status Changed'),
        ('COMMENT', 'Comment Added'),
        ('REASSIGN', 'Ticket Reassigned'),
        ('ATTACHMENT_ADDED', 'Attachment Added'),
        ('PRIORITY_CHANGE', 'Priority Changed'),
    )

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activity_timeline')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    status_change_log = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Timeline'
        verbose_name_plural = 'Activity Timelines'

    def __str__(self):
        return f"Activity on Ticket #{self.ticket.id} - {self.activity_type}"
