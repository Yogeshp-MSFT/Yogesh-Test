from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import EnquiryForm

def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('superadmin_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save()
            
            # Send Notification Email to Admin
            try:
                admin_subject = f"New Enquiry from {enquiry.name}: {enquiry.subject}"
                admin_message = f"You have received a new enquiry.\n\nName: {enquiry.name}\nEmail: {enquiry.email}\nSubject: {enquiry.subject}\nMessage:\n{enquiry.message}"
                send_mail(
                    admin_subject,
                    admin_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL], # Target admin email
                    fail_silently=False,
                )
                
                # Send Confirmation Email to User
                user_subject = "We received your enquiry - RBAC System"
                user_message = f"Hi {enquiry.name},\n\nThank you for reaching out to us. We have received your enquiry regarding '{enquiry.subject}' and will get back to you shortly.\n\nBest regards,\nThe RBAC System Team"
                send_mail(
                    user_subject,
                    user_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [enquiry.email],
                    fail_silently=False,
                )
                messages.success(request, "Your enquiry has been submitted successfully! We'll get back to you soon.")
            except Exception as e:
                error_msg = str(e)
                print(f"Email failed: {error_msg}")
                messages.error(request, f"Enquiry saved, but email failed: {error_msg}")
            
            return redirect('home')
        else:
            messages.error(request, "There was an error with your submission. Please check the form and try again.")
    else:
        form = EnquiryForm()
    
    return render(request, 'landing/landing_page.html', {'form': form})
