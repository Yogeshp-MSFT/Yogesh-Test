from django.urls import path
from . import views

urlpatterns = [
    path('superadmin/login/', views.login_view, name='login'),
    path('tenant/login/', views.company_login_view, name='company_login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create-user/', views.create_user, name='create_user'),
    path('edit/<int:pk>/', views.edit_user, name='edit_user'),
    path('delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    # Platform Owner Portal (SaaS)
    path('platform/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    
    path('manage-companies/', views.manage_companies, name='manage_companies'),
    path('create-company/', views.create_company, name='create_company'),
    path('platform/company/<int:company_id>/', views.company_detail, name='company_detail'),
    path('toggle-company/<int:company_id>/', views.toggle_company_status, name='toggle_company_status'),
    path('company-suspended/', views.company_suspended, name='company_suspended'),
    path('company/signup/', views.company_signup, name='company_signup'),
    path('subscription/', views.subscription_detail, name='subscription_detail'),

]
