from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Department

class SubUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'contact', 'department', 'role']

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Styling
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none bg-gray-50'
            })
            
            # Specific Placeholders
            if name == 'username':
                field.widget.attrs['placeholder'] = 'e.g. rahul_dev'
            elif name == 'email':
                field.widget.attrs['placeholder'] = 'e.g. rahul@company.com'
            elif name == 'contact':
                field.widget.attrs['placeholder'] = 'e.g. +91 98765 43210'
            elif name == 'password1':
                field.widget.attrs['placeholder'] = 'Enter a secure password'
            elif name == 'password2':
                field.widget.attrs['placeholder'] = 'Re-enter password to confirm'

        # Make department a ModelChoiceField that fetches from database
        self.fields['department'].queryset = Department.objects.all().order_by('name')
        self.fields['department'].empty_label = None

        # Apply hierarchical role restrictions for non-superusers
        if self.current_user and not self.current_user.is_superuser:
            if 'role' in self.fields:
                if self.current_user.role == 'MANAGER':
                    # Managers can only assign Editor, Employee
                    self.fields['role'].choices = [
                        choice for choice in self.fields['role'].choices
                        if choice[0] in ['EDITOR', 'VIEWER']
                    ]
                    # Ensure current selection is valid if editing (though this is CreationForm)
                else:
                    # Others (Company Admin) cannot assign Company Admin or system Admin
                    self.fields['role'].choices = [
                        choice for choice in self.fields['role'].choices
                        if choice[0] not in ['ADMIN', 'COMPANY_ADMIN']
                    ]

    def _post_clean(self):
        super()._post_clean()
        # Bypass password strength validation if the creator is a Company Admin or SuperAdmin
        if self.current_user and (self.current_user.is_superuser or self.current_user.role == 'COMPANY_ADMIN'):
            # Clear any password-related validation errors (length, commonity, etc.)
            if 'password1' in self._errors:
                del self._errors['password1']
            if 'password2' in self._errors:
                del self._errors['password2']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'contact', 'department', 'role']

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Styling
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full p-2 border rounded'
            })

        # Make department a ModelChoiceField that fetches from database
        self.fields['department'].queryset = Department.objects.all().order_by('name')
        self.fields['department'].empty_label = None

        # if the instance being edited is a superuser, don't expose role field at all
        if self.instance and getattr(self.instance, 'is_superuser', False):
            self.fields.pop('role', None)
            return

        # 🔥 Role restriction logic
        if current_user:
            # first apply role visibility rules for non-admin/non-manager users
            if not (current_user.is_superuser or current_user.role in ['MANAGER', 'COMPANY_ADMIN']):
                # only admins/managers can touch role or department; editors and
                # viewers should not even see these fields
                self.fields.pop('role', None)
                self.fields.pop('department', None)
                return

            # at this point current_user is either superuser, company admin, or manager
            # Apply hierarchical role restrictions for non-superusers
            if 'role' in self.fields and not current_user.is_superuser:
                if current_user.role == 'MANAGER':
                    # Managers can only assign Editor, Employee
                    self.fields['role'].choices = [
                        choice for choice in self.fields['role'].choices
                        if choice[0] in ['EDITOR', 'VIEWER']
                    ]
                else:
                    # Company Admins cannot assign Company Admin or system Admin
                    self.fields['role'].choices = [
                        choice for choice in self.fields['role'].choices
                        if choice[0] not in ['ADMIN', 'COMPANY_ADMIN']
                    ]

from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    
    class Meta:
        model = User
        fields = ['username', 'email', 'contact', 'whatsapp_available', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'VIEWER'   # Default role for normal signup
        if commit:
            user.save()
        return user
    def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       for field in self.fields.values():
          field.widget.attrs.update({
              'class': 'w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400'
        })



class CompanyWithAdminForm(forms.Form):
    company_name = forms.CharField(max_length=255)
    admin_username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full p-2 border rounded'
            })

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        if User.objects.filter(username=cleaned_data.get("admin_username")).exists():
            raise forms.ValidationError("Username already exists.")
        
        from .models import Company
        if Company.objects.filter(name=cleaned_data.get("company_name")).exists():
            raise forms.ValidationError("Company name already exists.")
        
        return cleaned_data

class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'contact', 'profile_photo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Styling
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400'
            })
        
        # Add labels and placeholders
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Enter first name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Enter last name'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Enter email address'})
        self.fields['contact'].widget.attrs.update({'placeholder': 'Enter contact number'})


class CompanySignupForm(forms.Form):
    company_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Your Organization Name'}))
    admin_username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Choose a username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'admin@company.com'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create secure password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full p-4 pl-12 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-medium text-slate-900 placeholder-slate-400'
            })

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        if User.objects.filter(username=cleaned_data.get("admin_username")).exists():
            raise forms.ValidationError("Username already exists.")
        
        from .models import Company
        if Company.objects.filter(name=cleaned_data.get("company_name")).exists():
            raise forms.ValidationError("Company name already exists.")
        
        return cleaned_data
