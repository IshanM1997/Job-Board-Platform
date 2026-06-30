"""
Registration forms, split by role.

Using two separate forms (rather than one form with a role dropdown)
keeps each signup flow simple and lets each role collect only the fields
that make sense for it; CandidateSignUpForm and EmployerSignUpForm both
inherit the username/email/password fields from UserCreationForm and
just fix the `role` they create.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class CandidateSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CANDIDATE
        if commit:
            user.save()
        return user


class EmployerSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.EMPLOYER
        if commit:
            user.save()
        return user
