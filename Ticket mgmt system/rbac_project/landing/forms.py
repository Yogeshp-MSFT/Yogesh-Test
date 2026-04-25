from django import forms
from .models import Enquiry

class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-sm text-sm text-jira-text placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none transition-all',
                'placeholder': 'Your Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-sm text-sm text-jira-text placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none transition-all',
                'placeholder': 'Work Email Address'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-sm text-sm text-jira-text placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none transition-all',
                'placeholder': 'Subject of Interest'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-sm text-sm text-jira-text placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none transition-all min-h-[120px]',
                'placeholder': 'Provide details about your organization\'s needs...'
            }),
        }
