"""
Application: a candidate's submission for a single JobListing, including
an uploaded resume and a pipeline `status` a recruiter moves through
applied -> reviewing -> interview -> offer -> hired, or rejected at any
point. Status transitions are exactly what applications/signals.py
listens for to fire email notifications.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse

from .validators import validate_resume_file


def resume_upload_path(instance, filename):
    """
    Stores resumes under media/resumes/<candidate_id>/<filename>, so a
    candidate's uploads are grouped together and don't collide with
    another candidate's file of the same name.
    """
    return f'resumes/{instance.candidate_id}/{filename}'


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        REVIEWING = 'reviewing', 'Reviewing'
        INTERVIEW = 'interview', 'Interview'
        OFFER = 'offer', 'Offer'
        HIRED = 'hired', 'Hired'
        REJECTED = 'rejected', 'Rejected'

    job = models.ForeignKey('jobs.JobListing', on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
        limit_choices_to={'role': 'candidate'},
    )
    resume = models.FileField(upload_to=resume_upload_path, validators=[validate_resume_file])
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    recruiter_notes = models.TextField(
        blank=True,
        help_text='Internal notes visible only to the hiring company, never shown to the candidate.',
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(fields=['job', 'candidate'], name='one_application_per_job_per_candidate'),
        ]

    def __str__(self):
        return f'{self.candidate} → {self.job} ({self.get_status_display()})'

    def get_absolute_url(self):
        return reverse('applications:application_detail', kwargs={'pk': self.pk})
