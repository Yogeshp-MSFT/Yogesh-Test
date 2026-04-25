from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class CompanyIsolationMiddleware:
    """
    Middleware to block access if the user's company is inactive.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            if request.user.company and not request.user.company.is_active:
                # Log the user out and redirect to login with a message
                from django.contrib.auth import logout
                logout(request)
                messages.error(request, "Your company account is deactivated. Please contact support.")
                return redirect('login')
        
        response = self.get_response(request)
        return response
