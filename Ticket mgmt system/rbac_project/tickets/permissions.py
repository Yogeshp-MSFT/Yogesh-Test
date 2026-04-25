from django.core.exceptions import PermissionDenied


class CanManageTicketsMixin:
    """
    Managers can CRUD all tickets.
    Admin has full access.
    Regular users like Editors and Employees can view and interact with assigned tickets.
    """
    
    def check_permission(self, user, action, ticket=None):
        """
        Check if user can perform an action on a ticket.
        Actions: 'create', 'view_all', 'view', 'update', 'delete', 'reassign', 'comment'
        """
        
        # Admin has full access
        if user.is_superuser or user.role == 'ADMIN':
            return True
        
        # Manager can do anything
        if user.role in ['MANAGER', 'COMPANY_ADMIN']:
            return True
        
        # Regular user permissions
        if action == 'create':
            return True
        elif action == 'view_all':
            return False
        elif action == 'view':
            return user == ticket.assignee if ticket else False
        elif action == 'update':
            return user == ticket.assignee if ticket else False
        elif action == 'delete':
            return False
        elif action == 'reassign':
            return user == ticket.assignee if ticket else False
        elif action == 'comment':
            return user == ticket.assignee if ticket else False
        
        return False


def check_ticket_access(user, ticket, action):
    """
    Helper function for checking ticket access permissions.
    
    Actions: 'view', 'create', 'update', 'delete', 'reassign', 'comment'
    """
    
    # Admin has full access
    if user.is_superuser or user.role == 'ADMIN':
        return True
    
    # Manager has full access
    if user.role in ['MANAGER', 'COMPANY_ADMIN']:
        return True
    
    # Regular user permissions
    if action == 'view':
        # Can view assigned tickets
        return user == ticket.assignee
    
    elif action == 'create':
        # All company users can create tickets
        return True
    
    elif action == 'update':
        # Can update status and description of assigned tickets
        return user == ticket.assignee
    
    elif action == 'delete':
        # Regular users cannot delete
        return False
    
    elif action == 'reassign':
        # Can only reassign their own assigned tickets
        return user == ticket.assignee
    
    elif action == 'comment':
        # Can comment on assigned tickets
        return user == ticket.assignee
    
    return False


def check_ticket_access_or_deny(user, ticket, action):
    """
    Wrapper that raises PermissionDenied if access is not allowed.
    """
    if not check_ticket_access(user, ticket, action):
        raise PermissionDenied(
            f"You do not have permission to {action} this ticket."
        )

