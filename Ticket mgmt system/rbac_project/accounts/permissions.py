def can_view(user):
    # Everyone except for anonymous/login‑less visitors should be able to
    # browse the user list; this helper is mostly documented by the dashboard
    # view rather than being invoked directly.
    return user.role in ['ADMIN', 'MANAGER', 'VIEWER', 'HYBRID', 'EDITOR', 'COMPANY_ADMIN']

def can_edit(user):
    # full editing privileges (including role/department changes) are reserved
    # for administrators and managers.  other roles may have limited field
    # access but that detail lives in the form class.
    return user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN']

def can_manage_roles(user):
    # both admins and managers can assign roles/departments
    return user.is_superuser or user.role in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN']
