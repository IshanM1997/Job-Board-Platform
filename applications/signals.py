"""
Email notifications, driven entirely by Django signals.

Two things need to trigger an email:

  1. A candidate submits a new Application -> notify the employer
     (the company's owner) that someone applied.
  2. A recruiter changes an existing Application's status -> notify the
     candidate that their pipeline stage changed.

Both are naturally `post_save` events on the Application model, but they
need to be told apart, and case (2) needs to know what the status
*changed from* to decide whether anything notification-worthy actually
happened (saving the same status twice, e.g. re-saving recruiter notes,
shouldn't re-send a "status changed" email).

The pattern used here is standard for this exact problem:
  - a `pre_save` receiver stashes the application's previous status (if
    any) onto the in-memory instance just before it's written, since by
    the time `post_save` fires the old value is already gone from the DB;
  - a `post_save` receiver reads `created` (provided by Django) to know
    whether this is a brand new application, and otherwise compares the
    stashed previous status against the new one.

Sending email itself goes through Django's `django.core.mail.send_mail`,
which respects EMAIL_BACKEND in settings — in local development this is
the console backend, so notifications print to the terminal instead of
requiring real SMTP credentials, while the call site code is identical
to what a production deployment would use.
"""

import logging

from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

from .models import Application

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Application)
def stash_previous_status(sender, instance, **kwargs):
    """
    Before an existing Application is saved, look up what its status
    used to be and stash it as a private attribute on the instance, so
    the post_save receiver below can tell whether the status actually
    changed. New (unsaved) instances have no previous row, so `_old_status`
    is left as None — post_save treats that as "not a status change",
    which is correct since `created=True` is checked first anyway.
    """
    if instance.pk is None:
        instance._old_status = None
        return

    try:
        previous = Application.objects.get(pk=instance.pk)
        instance._old_status = previous.status
    except Application.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Application)
def notify_on_application_created(sender, instance, created, **kwargs):
    """Notify the hiring company's owner when a new application comes in."""
    if not created:
        return

    employer = instance.job.company.owner
    if not employer or not employer.email:
        logger.warning(
            'No employer email on file for company %s; skipping new-application notification.',
            instance.job.company,
        )
        return

    context = {
        'application': instance,
        'job': instance.job,
        'candidate': instance.candidate,
        # reverse() only returns a relative path since signals run with no
        # request/domain in scope; a real deployment would prepend its
        # site domain (e.g. via django.contrib.sites or a SITE_URL setting)
        # before putting this in an email. Left relative here so the
        # project has no required external configuration to run.
        'application_path': reverse('applications:application_detail', kwargs={'pk': instance.pk}),
    }
    subject = f'New application: {instance.candidate.get_full_name() or instance.candidate.username} for {instance.job.title}'
    message = render_to_string('emails/new_application_employer.txt', context)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[employer.email],
        fail_silently=False,
    )


@receiver(post_save, sender=Application)
def notify_on_status_change(sender, instance, created, **kwargs):
    """Notify the candidate whenever a recruiter moves them to a new pipeline stage."""
    if created:
        return  # the "new application" receiver above already handled this save

    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status:
        return  # nothing actually changed about the status

    candidate = instance.candidate
    if not candidate.email:
        logger.warning('No email on file for candidate %s; skipping status-change notification.', candidate)
        return

    context = {
        'application': instance,
        'job': instance.job,
        'old_status': old_status,
        'new_status': instance.status,
        'new_status_display': instance.get_status_display(),
        'application_path': reverse('applications:application_detail', kwargs={'pk': instance.pk}),
    }
    subject = f'Update on your application for {instance.job.title}: {instance.get_status_display()}'
    message = render_to_string('emails/status_update_candidate.txt', context)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[candidate.email],
        fail_silently=False,
    )
