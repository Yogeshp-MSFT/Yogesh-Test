from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.views.generic import UpdateView, ListView
from django.urls import reverse_lazy
from django.contrib import messages

from .models import User, Company, Subscription, SubscriptionPlan
from .forms import SubUserCreationForm, CompanyWithAdminForm, UserProfileUpdateForm, CompanySignupForm
from .mixins import RoleRequiredMixin
from django.http import HttpResponseForbidden
from .permissions import can_edit,can_manage_roles
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout


# ================= LOG OUT =================

def logout_view(request):
    is_super = request.user.is_superuser
    logout(request)
    if is_super:
        return redirect('login')
    return redirect('company_login')

# ================= LOGIN VIEW =================

def login_view(request):
    """SuperAdmin Login Portal"""
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('superadmin_dashboard')
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)

    if form.is_valid():
        user = form.get_user()
        if not user.is_superuser:
            messages.error(request, "Access Denied. Company users must use Company Login.")
            return render(request, 'login.html', {'form': form})
            
        login(request, user)
        return redirect('superadmin_dashboard')

    # Add styling
    for field in form.fields.values():
        field.widget.attrs.update({
            'class': 'w-full p-4 pl-12 bg-transparent border-none focus:ring-0 text-slate-900 placeholder-slate-400 font-medium outline-none'
        })

    return render(request, 'login.html', {'form': form})


def company_login_view(request):
    """Company User Login (Admin, Manager, etc.)"""
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('superadmin_dashboard')
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)

    if form.is_valid():
        user = form.get_user()
        
        # Block SuperAdmins from logging in here
        if user.is_superuser:
            messages.error(request, "Access Denied. SuperAdmins must use SuperAdmin Login.")
            return render(request, 'company_login.html', {'form': form})

        # Block users of deactivated/suspended companies
        if user.company:
            if user.company.is_deleted:
                messages.error(request, "Access denied: Your company has been deleted.")
                return render(request, 'company_login.html', {'form': form})
            if not user.company.is_active:
                # Redirect to a dedicated suspension page
                return redirect('company_suspended')
            
        login(request, user)
        return redirect('dashboard')

    # Add styling
    for field in form.fields.values():
        field.widget.attrs.update({
            'class': 'w-full p-4 pl-12 bg-transparent border-none focus:ring-0 text-slate-900 placeholder-slate-400 font-medium outline-none'
        })

    return render(request, 'company_login.html', {'form': form})

# ================= DASHBOARD =================
@login_required
def dashboard(request):
    from django.db.models import Q, Case, When, IntegerField, Count
    from tickets.models import Ticket

    # Strict Portal Separation: SuperAdmin should use superadmin_dashboard
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')

    # Security check: logout if company was deleted or suspended
    if request.user.company:
        if request.user.company.is_deleted or not request.user.company.is_active:
            from django.contrib.auth import logout
            logout(request)
            if not request.user.company.is_active:
                return redirect('company_suspended')
            return redirect('company_login')

    # Filter users: Standard users never see SuperAdmin
    if request.user.is_superuser:
        users = User.objects.all().exclude(id=request.user.id)
    else:
        # Strict SaaS rule: standard users (Managers, etc.) see ONLY their company users
        # and NEVER see any SuperAdmin (there can be only one, and it's hidden)
        users = User.objects.filter(company=request.user.company).exclude(is_superuser=True)
        if request.user.role in ['MANAGER', 'COMPANY_ADMIN']:
            users = users.exclude(id=request.user.id)
        else:
            # Further restrict for normal users (EDITOR, VIEWER, etc.)
            users = users.exclude(role__in=['ADMIN', 'MANAGER', 'COMPANY_ADMIN']).exclude(id=request.user.id)

    # ===== EXTRACT FILTER PARAMETERS =====
    search_query = request.GET.get('search', '').strip()
    filter_department = request.GET.get('department', '').strip()
    filter_role = request.GET.get('role', '').strip()
    filter_project = request.GET.get('project', '').strip()

    ticket_results = None

    # ===== BUILD AVAILABLE FILTER OPTIONS =====
    from .models import Department
    
    # SuperAdmin sees all departments, others see their company's departments if applicable 
    # (assuming departments are global for now as per current schema, but we apply role-based filtering if needed)
    available_departments = list(Department.objects.all().order_by('name').values_list('name', flat=True))

    # Get available projects from Ticket model (apply company isolation)
    ticket_qs_for_projects = Ticket.objects.all()
    if not request.user.is_superuser:
        ticket_qs_for_projects = ticket_qs_for_projects.filter(company=request.user.company)
    
    if request.user.role not in ['ADMIN', 'MANAGER']:
        ticket_qs_for_projects = ticket_qs_for_projects.filter(assignee=request.user)
    available_projects = sorted(list(set(ticket_qs_for_projects.values_list('project_name', flat=True).distinct())))
    available_projects = [p for p in available_projects if p]  # Filter out empty strings

    # Get available roles from the visible user set only
    available_roles = sorted(list(set(users.values_list('role', flat=True).distinct())))
    # Explicitly remove high-privilege administrative roles from the filter as requested
    available_roles = [r for r in available_roles if r not in ['ADMIN', 'COMPANY_ADMIN'] and r]

    # ===== APPLY CATEGORIZED FILTERS =====
    if filter_department:
        # filter_department is a department name string, find the Department object
        try:
            dept_obj = Department.objects.get(name=filter_department)
            users = users.filter(department=dept_obj)
        except Department.DoesNotExist:
            # If department doesn't exist, no results
            users = users.none()

    if filter_role:
        users = users.filter(role=filter_role)

    if filter_project:
        # Get tickets from the specified project
        if request.user.is_superuser:
            project_tickets = Ticket.objects.filter(project_name=filter_project)
        else:
            project_tickets = Ticket.objects.filter(project_name=filter_project, company=request.user.company)
            if request.user.role not in ['MANAGER', 'COMPANY_ADMIN']:
                project_tickets = project_tickets.filter(assignee=request.user)
        
        assignee_ids = list(project_tickets.exclude(assignee__isnull=True).values_list('assignee', flat=True).distinct())
        if assignee_ids:
            users = users.filter(id__in=assignee_ids)
        else:
            users = users.none()

    # ===== TEXT SEARCH (search_query) =====
    if search_query:
        # Build a searchable user set that may include the current user
        if request.user.is_superuser:
            searchable_users = User.objects.all()
        elif request.user.role in ['MANAGER', 'COMPANY_ADMIN']:
            searchable_users = User.objects.filter(company=request.user.company).exclude(is_superuser=True)
        else:
            searchable_users = User.objects.filter(company=request.user.company).exclude(role__in=['MANAGER', 'COMPANY_ADMIN']).exclude(is_superuser=True)

        # First try to find users by username or email within the searchable set.
        user_matches = searchable_users.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query))

        if user_matches.exists():
            # If we found user(s), show them and do NOT show ticket search results.
            users = user_matches
            ticket_results = None
        else:
            # No direct user matches — search tickets (respecting user permissions)
            if request.user.is_superuser:
                ticket_qs = Ticket.objects.all()
            else:
                ticket_qs = Ticket.objects.filter(company=request.user.company)
                if request.user.role not in ['ADMIN', 'MANAGER', 'COMPANY_ADMIN']:
                    ticket_qs = ticket_qs.filter(assignee=request.user)

            ticket_filter = (
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(project_name__icontains=search_query)
                # department is a FK; search by its name
                | Q(department__name__icontains=search_query)
            )
            # also allow searching by numeric id
            if search_query.isdigit():
                try:
                    ticket_filter = ticket_filter | Q(id=int(search_query))
                except ValueError:
                    pass

            matching_tickets = ticket_qs.filter(ticket_filter)

            if matching_tickets.exists():
                # Try to resolve matching tickets back to their assignees (users).
                assignee_ids = list(matching_tickets.exclude(assignee__isnull=True).values_list('assignee', flat=True))
                if assignee_ids:
                    # Restrict to users that are visible in the searchable set (this allows matching the current user)
                    assignee_users = searchable_users.filter(id__in=assignee_ids)
                    if assignee_users.exists():
                        # If we found assignee users, show them instead of ticket results.
                        users = assignee_users.distinct()
                        ticket_results = None
                    else:
                        # No visible assignee users — fall back to showing ticket results.
                        ticket_results = matching_tickets
                else:
                    # Matching tickets but no assignees — show ticket results.
                    ticket_results = matching_tickets
            else:
                # No tickets matched either — return empty user set so template shows "No users found"
                users = users.none()
                ticket_results = None

    # ===== ORDER AND ANNOTATE RESULTS =====
    users = users.annotate(
        role_priority=Case(
            When(role='MANAGER', then=1),
            When(role='EDITOR', then=2),
            When(role='VIEWER', then=3),
            default=4,
            output_field=IntegerField(),
        ),
        assigned_ticket_count=Count('tickets_assigned_to_me')
    ).order_by('role_priority', 'username')

    # Prefetch assigned tickets to avoid N+1 when rendering links in template
    users = users.prefetch_related('tickets_assigned_to_me')

    # ===== SUBSCRIPTION INFO =====
    subscription = None
    if not request.user.is_superuser and request.user.company:
        subscription = Subscription.objects.filter(company=request.user.company, is_active=True).first()

    # ===== BUILD CONTEXT =====
    context = {
        'users': users,
        'search_query': search_query,
        'filter_department': filter_department,
        'filter_role': filter_role,
        'filter_project': filter_project,
        'available_departments': available_departments,
        'available_roles': available_roles,
        'available_projects': available_projects,
        'subscription': subscription,
    }
    if ticket_results is not None:
        context['ticket_results'] = ticket_results
    return render(request, 'dashboard.html', context)


# ================= ADMIN CREATE USERS =================
@login_required
def create_user(request):

    # only admins and managers may create subordinate accounts; editors/hybrids
    # can no longer hit this view because they are not allowed to assign roles
    # or departments.
    if not (request.user.is_superuser or request.user.role in ['MANAGER', 'COMPANY_ADMIN']):
       return HttpResponseForbidden("Permission Denied")

    form = SubUserCreationForm(request.POST or None, current_user=request.user)

    if request.method == "POST":
        print("POST DATA:", request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            # assign creator's company to the new user
            user.company = request.user.company
            # mark that this user was created by admin
            user.created_by_admin = True
            # 🚫 Prevent assigning ADMIN manually
            if user.role == 'ADMIN':
                user.role = 'VIEWER'
            user.save()
            print("USER SAVED:", user)
            return redirect('dashboard')
        else:
            print("FORM ERRORS:", form.errors)
    return render(request, 'create_user.html', {'form': form})



# ================= EDIT USER =================

from .forms import UserUpdateForm

@login_required
def edit_user(request, pk):

    if request.user.is_superuser:
        user_obj = get_object_or_404(User, pk=pk)
    else:
        user_obj = get_object_or_404(User, pk=pk, company=request.user.company)

    # ❌ Only non-superusers are blocked from editing a superuser
    if user_obj.is_superuser and not request.user.is_superuser:
        return HttpResponseForbidden("Admin cannot be edited")

    # ✅ Permission Rules
    if request.user.is_superuser:
        allowed = True
    elif request.user.role in ['MANAGER', 'COMPANY_ADMIN', 'ADMIN']:
        # project managers can edit any account except superusers (admin)
        # ❌ NEW: Prevent Managers/Editors from editing Company Admins
        if request.user.role == 'MANAGER' and user_obj.role == 'COMPANY_ADMIN':
            allowed = False
        else:
            allowed = not user_obj.is_superuser
    elif request.user.role == 'EDITOR':
        # editors stay limited to viewer (Employee) profiles
        # ❌ NEW: Prevent Editors from editing Company Admins (already limited but making explicit)
        if user_obj.role == 'COMPANY_ADMIN':
            allowed = False
        else:
            allowed = user_obj.role == 'VIEWER'
    else:
        allowed = False

    if not allowed:
        return HttpResponseForbidden("Permission Denied")

    form = UserUpdateForm(
        request.POST or None,
        instance=user_obj,
        current_user=request.user
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('dashboard')

    # 🔥 VERY IMPORTANT — Always return response
    return render(request, 'edit_user.html', {'form': form})
  

from .forms import UserRegistrationForm

def register_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserRegistrationForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect('login')

    return render(request, 'register.html', {'form': form})


# ================= DELETE USER =================

@login_required
def delete_user(request, pk):

    if request.user.is_superuser:
        user_obj = get_object_or_404(User, pk=pk)
    else:
        user_obj = get_object_or_404(User, pk=pk, company=request.user.company)

    # ❌ Nobody can delete themselves
    if user_obj.id == request.user.id:
        return HttpResponseForbidden("Cannot delete your own account")

    # ❌ Non-superusers cannot delete a superuser
    if user_obj.is_superuser and not request.user.is_superuser:
        return HttpResponseForbidden("Cannot delete admin users")

    # ✅ Permission Rules
    if request.user.is_superuser:
        allowed = True
    elif request.user.role in ['MANAGER', 'COMPANY_ADMIN', 'ADMIN']:
        # manager may delete anyone except superusers
        # ❌ NEW: Prevent Managers from deleting Company Admins
        if request.user.role == 'MANAGER' and user_obj.role == 'COMPANY_ADMIN':
            allowed = False
        else:
            allowed = not user_obj.is_superuser
    else:
        allowed = False

    if not allowed:
        return HttpResponseForbidden("Permission Denied")

    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f'User "{username}" has been deleted successfully.')
        return redirect('dashboard')

    # GET request: show confirmation page
    return render(request, 'delete_user.html', {'user': user_obj})


# ================= SUPERADMIN PORTAL (SaaS) =================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def superadmin_dashboard(request):
    company_count = Company.objects.filter(is_deleted=False, is_active=True).count()
    active_companies = Company.objects.filter(is_active=True, is_deleted=False).count()
    # Count only active users belonging to active, non-deleted companies
    total_users = User.objects.filter(
        is_active=True, 
        company__is_deleted=False, 
        company__is_active=True
    ).exclude(is_superuser=True).count()
    companies = Company.objects.filter(is_deleted=False, is_active=True).prefetch_related('users', 'subscriptions').order_by('-created_at')[:5]  # Show latest 5 active
    
    print(f"DEBUG: company_count={company_count}, active={active_companies}, total_users={total_users}")
    
    context = {
        'company_count': company_count,
        'active_companies': active_companies,
        'inactive_companies': company_count - active_companies,
        'total_users': total_users,
        'companies': companies,
    }
    return render(request, 'superadmin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_company(request):
    form = CompanyWithAdminForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            from django.db import transaction
            try:
                with transaction.atomic():
                    # Create Company
                    company = Company.objects.create(
                        name=form.cleaned_data['company_name']
                    )
                    # Create Company Admin (Manager)
                    User.objects.create_user(
                        username=form.cleaned_data['admin_username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        role='COMPANY_ADMIN',
                        company=company,
                        created_by_admin=True,
                        is_company_admin=True
                    )
                    messages.success(request, f"Company '{company.name}' and its admin created successfully.")
                    return redirect('manage_companies')
            except Exception as e:
                messages.error(request, f"Error creating company: {str(e)}")
    
    return render(request, 'create_company.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_companies(request):
    # Show only active companies in the primary list, or handle suspended ones clearly
    # Usually manage_companies should show ALL non-deleted, but user wants them GONE if "deleted"
    companies = Company.objects.filter(is_deleted=False).prefetch_related('users', 'subscriptions').order_by('-created_at')
    return render(request, 'manage_companies.html', {'companies': companies})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_company(request, company_id):
    company = get_object_or_404(Company, id=company_id, is_deleted=False)
    company.is_deleted = True
    company.save()
    messages.success(request, f"Company '{company.name}' has been deleted successfully.")
    return redirect('manage_companies')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_company_status(request, company_id):
    company = get_object_or_404(Company, id=company_id, is_deleted=False)
    company.is_active = not company.is_active
    company.save()
    status = "activated" if company.is_active else "deactivated"
    messages.success(request, f"Company '{company.name}' has been {status}.")
    return redirect('manage_companies')

def company_suspended(request):
    """
    Publicly accessible view to show suspension message.
    """
    return render(request, 'company_suspended.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def company_detail(request, company_id):
    from tickets.models import Ticket
    company = get_object_or_404(Company, id=company_id, is_deleted=False)
    
    # Statistics
    # Statistics override: only count active users
    admin_user = company.users.filter(is_company_admin=True, is_active=True).first()
    users = company.users.filter(is_active=True).exclude(is_superuser=True).order_by('username')
    tickets = company.tickets.all().order_by('-created_at')
    
    # Fetch active subscription
    subscription = company.subscriptions.filter(is_active=True).first()
    
    context = {
        'company': company,
        'admin_user': admin_user,
        'total_users': users.count(),
        'total_tickets': tickets.count(),
        'users': users,
        'tickets': tickets,
        'subscription': subscription,
    }
    return render(request, 'superadmin_company_detail.html', context)


@login_required
def profile_view(request):
    """
    Logged in user can view and edit their own profile.
    """
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserProfileUpdateForm(instance=request.user)

    return render(request, 'profile.html', {'form': form})


def company_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    form = CompanySignupForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            from django.db import transaction
            try:
                with transaction.atomic():
                    # Create Company
                    company = Company.objects.create(
                        name=form.cleaned_data['company_name'],
                        is_self_registered=True
                    )
                    # Create Admin User
                    user = User.objects.create_user(
                        username=form.cleaned_data['admin_username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        role='COMPANY_ADMIN',
                        company=company,
                        is_company_admin=True,
                        created_by_admin=False
                    )
                    # Auto login
                    user = authenticate(username=user.username, password=form.cleaned_data['password'])
                    if user:
                        login(request, user)
                        messages.success(request, f"Welcome to RBAC System! Your company '{company.name}' has been registered.")
                        return redirect('dashboard')
            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
    
    return render(request, 'company_signup.html', {'form': form})


@login_required
def subscription_detail(request):
    if request.user.is_superuser:
        company_id = request.GET.get('company_id')
        if company_id:
            company = get_object_or_404(Company, id=company_id)
            subscription = Subscription.objects.filter(company=company, is_active=True).first()
        else:
            return redirect('manage_companies')
    else:
        company = request.user.company
        subscription = Subscription.objects.filter(company=company, is_active=True).first()
    
    # Fetch all available plans for the "Upgrade" section
    all_plans = SubscriptionPlan.objects.all().order_by('duration_days')
    
    return render(request, 'subscription_detail.html', {
        'subscription': subscription,
        'company': company,
        'all_plans': all_plans
    })


