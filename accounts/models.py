"""
Custom User model for role-based auth.

Rather than bolting a "profile" model onto Django's default User, this
project swaps in a custom User (AUTH_USER_MODEL = 'accounts.User') with a
`role` field baked in. This is the cleanest way to do role-based auth in
Django: the role is available on every authenticated request as
`request.user.role`, and it can be checked directly in templates,
decorators, and querysets without an extra join.

Two roles exist:
  - CANDIDATE: applies to jobs, uploads a resume per application.
  - EMPLOYER: belongs to (and can manage) one or more Company profiles,
    posts job listings, and reviews applications.

A `is_candidate` / `is_employer` property pair is provided for
readability at call sites (`if request.user.is_employer:` reads better
than comparing strings everywhere).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CANDIDATE = 'candidate', 'Candidate'
        EMPLOYER = 'employer', 'Employer'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text='Determines what this account can do: post jobs (employer) or apply to them (candidate).',
    )

    # Optional fields useful regardless of role.
    phone_number = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_candidate(self):
        return self.role == self.Role.CANDIDATE

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER
