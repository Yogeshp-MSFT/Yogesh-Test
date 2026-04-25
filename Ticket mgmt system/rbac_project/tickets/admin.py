from django.contrib import admin
from .models import Ticket, Attachment, ActivityTimeline


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'priority', 'status', 'assignee', 'assigned_to', 'created_at')
    list_filter = ('priority', 'status', 'department', 'created_at')
    search_fields = ('title', 'description', 'project_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'priority', 'status')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assignee')
        }),
        ('Details', {
            'fields': ('department', 'project_name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at', 'ticket')
    search_fields = ('ticket__title', 'file')
    readonly_fields = ('uploaded_at',)


@admin.register(ActivityTimeline)
class ActivityTimelineAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'activity_type', 'user', 'timestamp')
    list_filter = ('activity_type', 'timestamp', 'ticket')
    search_fields = ('ticket__title', 'comment', 'status_change_log')
    readonly_fields = ('timestamp',)

