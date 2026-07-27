
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SchoolRegistrationForm

def register_school_view(request):
    if request.method == 'POST':
        form = SchoolRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            # Redirect to a success page or back to the landing page with a message
            messages.success(request, "Success! Your application and payment proof have been received. Our team will review this and send your login credentials to your email within 24 hours.")
            return redirect('public_landing')
    else:
        form = SchoolRegistrationForm()

    return render(request, 'schools_manager/register_school.html', {'form': form})