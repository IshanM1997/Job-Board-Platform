"""
Application views.

Three audiences, three different permission stories:
  - A candidate may apply to a job (once) and view only their own
    applications.
  - An employer/recruiter may view and update the status of applications
    submitted to listings owned by their own company — never another
    company's applications, and never edit anything as the candidate.
  - Saving a status change in `update_status` is what triggers the
    candidate notification email, via the post_save signal in
    applications/signals.py — this view does nothing email-related
    itself, which is the point of using signals: the notification logic
    isn't duplicated at every call site that might change a status.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from accounts.decorators import role_required
from jobs.models import JobListing
from .forms import ApplicationForm, ApplicationStatusForm
from .models import Application


@role_required('candidate')
def apply_to_job(request, job_pk):
    job = get_object_or_404(JobListing, pk=job_pk, is_active=True)

    if Application.objects.filter(job=job, candidate=request.user).exists():
        messages.info(request, "You've already applied to this job.")
        return redirect('jobs:job_detail', pk=job.pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.candidate = request.user
            try:
                application.save()
            except IntegrityError:
                # Defends against a race: two near-simultaneous submits
                # for the same job+candidate. The unique constraint on
                # the model is the real guarantee; this just turns the
                # resulting DB error into a friendly message instead of
                # a 500.
                messages.info(request, "You've already applied to this job.")
                return redirect('jobs:job_detail', pk=job.pk)

            messages.success(request, 'Your application was submitted!')
            return redirect('applications:application_detail', pk=application.pk)
    else:
        form = ApplicationForm()

    return render(request, 'applications/apply_form.html', {'form': form, 'job': job})


@login_required
def application_detail(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('job', 'job__company', 'candidate'), pk=pk
    )

    is_owning_candidate = application.candidate_id == request.user.id
    is_owning_employer = request.user.is_employer and application.job.company.owner_id == request.user.id

    if not (is_owning_candidate or is_owning_employer):
        raise PermissionDenied('You do not have access to this application.')

    status_form = None
    if is_owning_employer:
        status_form = ApplicationStatusForm(instance=application)

    return render(request, 'applications/application_detail.html', {
        'application': application,
        'is_owning_employer': is_owning_employer,
        'status_form': status_form,
    })


@role_required('employer')
def update_status(request, pk):
    application = get_object_or_404(Application.objects.select_related('job__company'), pk=pk)
    if application.job.company.owner_id != request.user.id:
        raise PermissionDenied('You can only manage applications for your own company.')

    if request.method == 'POST':
        form = ApplicationStatusForm(request.POST, instance=application)
        if form.is_valid():
            # This save is what fires applications.signals.notify_on_status_change
            # if the status field actually changed.
            form.save()
            messages.success(request, 'Application updated.')
    return redirect('applications:application_detail', pk=application.pk)


@role_required('employer')
def pipeline(request, job_pk):
    """A recruiter's view of every application for one of their job listings, grouped by status."""
    job = get_object_or_404(JobListing, pk=job_pk)
    if job.company.owner_id != request.user.id:
        raise PermissionDenied('You can only view the pipeline for your own listings.')

    applications = job.applications.select_related('candidate').order_by('status', '-applied_at')

    grouped = {choice_value: [] for choice_value, _ in Application.Status.choices}
    for app in applications:
        grouped[app.status].append(app)

    return render(request, 'applications/pipeline.html', {
        'job': job,
        'grouped': grouped,
        'status_choices': Application.Status.choices,
    })
