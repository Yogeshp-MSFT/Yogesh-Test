from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Department


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'role', 'department', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Role Management', {'fields': ('role', 'department')}),
    )


admin.site.register(Department, DepartmentAdmin)
admin.site.register(User, CustomUserAdmin)

