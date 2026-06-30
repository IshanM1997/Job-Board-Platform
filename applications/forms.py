from django import forms

from .models import Application


class ApplicationForm(forms.ModelForm):
    """Used by a candidate to apply to a job: resume + optional cover letter."""

    class Meta:
        model = Application
        fields = ['resume', 'cover_letter']
        widgets = {
            'cover_letter': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': "Tell the hiring team why you're a great fit (optional).",
            }),
        }


class ApplicationStatusForm(forms.ModelForm):
    """
    Used by a recruiter/employer to move an application through the
    pipeline. Saving this form with a changed `status` is exactly what
    applications/signals.py listens for to notify the candidate.
    """

    class Meta:
        model = Application
        fields = ['status', 'recruiter_notes']
        widgets = {
            'recruiter_notes': forms.Textarea(attrs={'rows': 4}),
        }
