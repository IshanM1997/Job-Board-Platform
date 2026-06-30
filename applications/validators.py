"""
Validators for resume uploads: restrict file extension and file size.
Kept as a standalone module so both the model field and any form-level
validation can reuse the exact same checks.
"""

import os

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_resume_file(file):
    """
    Validates a single uploaded file against the project's allowed
    extensions and max size. Raises django.core.exceptions.ValidationError
    on failure, which Django automatically surfaces as a form field error.
    """
    ext = os.path.splitext(file.name)[1].lower()
    allowed = getattr(settings, 'ALLOWED_RESUME_EXTENSIONS', ['.pdf', '.doc', '.docx'])
    if ext not in allowed:
        raise ValidationError(
            f'Unsupported file type "{ext}". Allowed types: {", ".join(allowed)}.'
        )

    max_size_mb = getattr(settings, 'MAX_RESUME_UPLOAD_SIZE_MB', 5)
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValidationError(
            f'File is too large ({file.size / (1024 * 1024):.1f} MB). Maximum allowed is {max_size_mb} MB.'
        )
