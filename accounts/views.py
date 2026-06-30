"""
Auth views: separate signup flows for candidates and employers, plus a
single dashboard view that branches its content (but not its URL) by
role — a candidate visiting /accounts/dashboard/ sees their applications,
an employer sees their companies and listings.
"""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect

from .forms import CandidateSignUpForm, EmployerSignUpForm


class JobBoardLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


def signup_landing(request):
    """A simple chooser page: 'I'm a candidate' vs 'I'm an employer'."""
    return render(request, 'registration/signup_landing.html')


def candidate_signup(request):
    if request.method == 'POST':
        form = CandidateSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:dashboard')
    else:
        form = CandidateSignUpForm()
    return render(request, 'registration/candidate_signup.html', {'form': form})


def employer_signup(request):
    if request.method == 'POST':
        form = EmployerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('companies:company_create')
    else:
        form = EmployerSignUpForm()
    return render(request, 'registration/employer_signup.html', {'form': form})


@login_required
def dashboard(request):
    if request.user.is_employer:
        from companies.models import Company
        from jobs.models import JobListing
        companies = Company.objects.filter(owner=request.user)
        listings = JobListing.objects.filter(company__owner=request.user).order_by('-created_at')
        return render(request, 'accounts/employer_dashboard.html', {
            'companies': companies,
            'listings': listings,
        })
    else:
        from applications.models import Application
        applications = (
            Application.objects.filter(candidate=request.user)
            .select_related('job', 'job__company')
            .order_by('-applied_at')
        )
        return render(request, 'accounts/candidate_dashboard.html', {
            'applications': applications,
        })
