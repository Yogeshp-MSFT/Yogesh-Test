from django.core.exceptions import PermissionDenied

class CompanyIsolationMixin:
    """
    Mixin to enforce company isolation at the queryset level.
    SuperAdmins see everything, others see only their company data.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        if user.company:
            return queryset.filter(company=user.company)
        
        # If user has no company and isn't a superuser, they see nothing by default
        return queryset.none()


class RoleRequiredMixin:
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
