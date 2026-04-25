from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Ticket, Attachment, ActivityTimeline
from .permissions import check_ticket_access_or_deny
from accounts.mixins import RoleRequiredMixin, CompanyIsolationMixin
from accounts.models import User


class TicketAccessMixin(LoginRequiredMixin):
    """
    Custom mixin to check ticket access based on user role and permissions.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        Check if user has access to this ticket.
        """
        if hasattr(self, 'object'):
            ticket = self.object
        else:
            # For list views
            return super().dispatch(request, *args, **kwargs)
        
        # Check access
        try:
            action = self.get_action_name()
            check_ticket_access_or_deny(request.user, ticket, action)
        except PermissionDenied:
            return HttpResponseForbidden("You don't have permission to access this ticket.")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_action_name(self):
        """
        Determine the action based on the HTTP method.
        """
        method_to_action = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        return method_to_action.get(self.request.method, 'view')


class TicketListView(LoginRequiredMixin, CompanyIsolationMixin, ListView):
    """
    List all tickets (all users can view all tickets).
    """
    model = Ticket
    template_name = 'tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        # Respect company isolation
        queryset = super().get_queryset()
        
        # Search filtering
        q = self.request.GET.get('q', '').strip()
        if q:
            # search title, description, project, or department name
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(project_name__icontains=q) |
                Q(department__name__icontains=q)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_create_ticket'] = self.request.user.is_superuser or self.request.user.company is not None
        # preserve search query across pagination links
        context['search_query'] = self.request.GET.get('q', '')
        return context


class TicketDetailView(LoginRequiredMixin, CompanyIsolationMixin, DetailView):
    """
    Display ticket details with activity timeline and attachments.
    """
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    pk_url_kwarg = 'pk'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.object
        user = self.request.user
        
        # Add activity timeline
        context['activities'] = ticket.activity_timeline.all()
        context['attachments'] = ticket.attachments.all()
        
        # Permission checks:
        # - Admins and Managers can update/reassign/comment/attach/delete
        # - Other users can only update/reassign/comment/attach if they are the assignee
        is_admin_or_manager = user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN']
        is_assignee = user == ticket.assignee
        
        context['can_update'] = is_admin_or_manager or is_assignee
        context['can_reassign'] = is_admin_or_manager or is_assignee
        # attaching files uses same permission set as commenting
        context['can_comment'] = is_admin_or_manager or is_assignee
        context['can_attach'] = context['can_comment']
        # Only superadmin, PLATFORM ADMIN or company-level admins can delete
        context['can_delete'] = user.is_superuser or user.role in ['ADMIN', 'COMPANY_ADMIN', 'MANAGER']
        if user.is_superuser:
            context['all_users'] = User.objects.filter(is_active=True).exclude(id=user.id)
        else:
            # Same company AND Role in [EDITOR, VIEWER]
            context['all_users'] = User.objects.filter(
                is_active=True, 
                company=user.company,
                role__in=['MANAGER', 'EDITOR', 'VIEWER']
            ).exclude(id=user.id)
        
        return context


class TicketCreateView(RoleRequiredMixin, CompanyIsolationMixin, CreateView):
    """
    Create a new ticket (only for Admin and Manager).
    """
    model = Ticket
    template_name = 'tickets/ticket_form.html'
    fields = ['title', 'assignee', 'description', 'priority', 'department', 'project_name']
    success_url = reverse_lazy('ticket-list')
    allowed_roles = ['ADMIN', 'MANAGER', 'COMPANY_ADMIN', 'EDITOR', 'VIEWER']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser:
            # Filter assignee: Same company AND Role in [EDITOR, VIEWER]
            # Exclude Company Admins and Platform Admins
            form.fields['assignee'].queryset = User.objects.filter(
                is_active=True, 
                company=user.company,
                role__in=['MANAGER', 'EDITOR', 'VIEWER']
            ).exclude(id=user.id)
        return form

    def form_valid(self, form):
        form.instance.assigned_to = self.request.user
        form.instance.company = self.request.user.company
        response = super().form_valid(form)
        
        # Log activity
        ActivityTimeline.objects.create(
            ticket=self.object,
            user=self.request.user,
            activity_type='STATUS_CHANGE',
            status_change_log=f'Ticket created in OPEN status'
        )
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser:
            context['all_users'] = User.objects.filter(is_active=True).exclude(id=user.id)
        else:
            # Same company AND Role in [EDITOR, VIEWER]
            context['all_users'] = User.objects.filter(
                is_active=True, 
                company=user.company,
                role__in=['MANAGER', 'EDITOR', 'VIEWER']
            ).exclude(id=user.id)
        return context


class TicketUpdateView(LoginRequiredMixin, CompanyIsolationMixin, UpdateView):
    """
    Update ticket (Managers can update any ticket, Users can only update assigned).
    """
    model = Ticket
    template_name = 'tickets/ticket_form.html'
    fields = ['title', 'description', 'priority', 'status', 'department', 'project_name']
    success_url = reverse_lazy('ticket-detail')
    pk_url_kwarg = 'pk'

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        user = self.request.user
        
        # Enforce update permissions: Admins and Managers can update any ticket,
        # but other users can only update if they are the assignee
        is_admin_or_manager = user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN']
        is_assignee = user == ticket.assignee
        
        if not (is_admin_or_manager or is_assignee):
            raise PermissionDenied("You don't have permission to update this ticket.")
        
        return ticket

    def form_valid(self, form):
        old_ticket = Ticket.objects.get(pk=self.object.pk)
        response = super().form_valid(form)
        
        # Log status changes
        if old_ticket.status != form.instance.status:
            ActivityTimeline.objects.create(
                ticket=self.object,
                user=self.request.user,
                activity_type='STATUS_CHANGE',
                status_change_log=f'Status changed from {old_ticket.status} to {form.instance.status}'
            )
        
        # Log priority changes
        if old_ticket.priority != form.instance.priority:
            ActivityTimeline.objects.create(
                ticket=self.object,
                user=self.request.user,
                activity_type='PRIORITY_CHANGE',
                status_change_log=f'Priority changed from {old_ticket.priority} to {form.instance.priority}'
            )
        
        return response

    def get_success_url(self):
        return reverse_lazy('ticket-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser:
            context['all_users'] = User.objects.filter(is_active=True).exclude(id=user.id)
        else:
            # Same company AND Role in [EDITOR, VIEWER]
            context['all_users'] = User.objects.filter(
                is_active=True, 
                company=user.company,
                role__in=['MANAGER', 'EDITOR', 'VIEWER']
            ).exclude(id=user.id)
        return context


class TicketDeleteView(RoleRequiredMixin, CompanyIsolationMixin, DeleteView):
    """
    Delete ticket (only Admin can delete).
    """
    model = Ticket
    template_name = 'tickets/ticket_confirm_delete.html'
    success_url = reverse_lazy('ticket-list')
    pk_url_kwarg = 'pk'
    allowed_roles = ['ADMIN', 'MANAGER', 'COMPANY_ADMIN']


class TicketReassignView(LoginRequiredMixin, CompanyIsolationMixin, UpdateView):
    """
    Reassign ticket to another user (Managers and assignee can reassign).
    """
    model = Ticket
    template_name = 'tickets/ticket_reassign.html'
    fields = ['assignee']
    pk_url_kwarg = 'pk'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser:
            # Filter assignee: Same company AND Role in [EDITOR, VIEWER]
            # Exclude Company Admins and Platform Admins
            form.fields['assignee'].queryset = User.objects.filter(
                is_active=True, 
                company=user.company,
                role__in=['MANAGER', 'EDITOR', 'VIEWER']
            ).exclude(id=user.id)
        return form

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        user = self.request.user
        
        # Check permissions
        if not (user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN'] or user == ticket.assignee):
            raise PermissionDenied("You don't have permission to reassign this ticket.")
        
        return ticket

    def form_valid(self, form):
        old_assignee = self.object.assignee
        response = super().form_valid(form)
        
        # Log reassignment
        ActivityTimeline.objects.create(
            ticket=self.object,
            user=self.request.user,
            activity_type='REASSIGN',
            status_change_log=f'Ticket reassigned from {old_assignee} to {form.instance.assignee}'
        )
        
        return response

    def get_success_url(self):
        return reverse_lazy('ticket-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser:
            context['all_users'] = User.objects.filter(is_active=True).exclude(id=user.id)
        else:
            # Same company AND Role in [EDITOR, VIEWER]
            context['all_users'] = User.objects.filter(
                is_active=True, 
                company=user.company,
                role__in=['MANAGER', 'EDITOR', 'VIEWER']
            ).exclude(id=user.id)
        return context

class AddCommentView(LoginRequiredMixin, CompanyIsolationMixin, UpdateView):
    """
    Add comment to ticket (Assigned user and Managers).
    """
    model = Ticket
    fields = []
    pk_url_kwarg = 'pk'

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        user = self.request.user
        
        # Check if user can comment
        if not (user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN'] or user == ticket.assignee):
            raise PermissionDenied("You don't have permission to comment on this ticket.")
        
        return ticket

    def post(self, request, *args, **kwargs):
        ticket = self.get_object()
        comment_text = request.POST.get('comment', '').strip()
        
        if not comment_text:
            return JsonResponse({'error': 'Comment cannot be empty'}, status=400)
        
        # Create comment activity log
        activity = ActivityTimeline.objects.create(
            ticket=ticket,
            user=request.user,
            activity_type='COMMENT',
            comment=comment_text
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': activity.id,
                'user': request.user.username,
                'comment': comment_text,
                'timestamp': activity.timestamp.isoformat(),
            }
        })


class AddAttachmentView(LoginRequiredMixin, UpdateView):
    """
    Add attachment to ticket (Assigned user and Managers).
    """
    model = Ticket
    fields = []
    pk_url_kwarg = 'pk'

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        user = self.request.user
        
        # Check if user can add attachment
        if not (user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN'] or user == ticket.assignee):
            raise PermissionDenied("You don't have permission to add attachments to this ticket.")
        
        return ticket

    def post(self, request, *args, **kwargs):
        ticket = self.get_object()
        
        if 'file' not in request.FILES:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'No file provided'}, status=400)
            messages.error(request, 'No file provided for attachment.')
            return redirect('ticket-detail', pk=ticket.pk)
        
        attachment = Attachment.objects.create(
            ticket=ticket,
            file=request.FILES['file'],
            uploaded_by=request.user
        )
        
        # Log attachment activity
        ActivityTimeline.objects.create(
            ticket=ticket,
            user=request.user,
            activity_type='ATTACHMENT_ADDED',
            status_change_log=f'Attachment: {attachment.file.name}'
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'attachment': {
                    'id': attachment.id,
                    'filename': attachment.file.name,
                    'uploaded_by': request.user.username,
                    'uploaded_at': attachment.uploaded_at.isoformat(),
                }
            })
        messages.success(request, 'Attachment uploaded successfully.')
        return redirect('ticket-detail', pk=ticket.pk)

