"""
Role-based access control helpers.

Django doesn't ship an opinionated way to say "only employers can see
this view" — `login_required` only checks *that* someone is logged in,
not *which kind* of account they have. These decorators/mixins layer
role checks on top of that, and are the building blocks every employer-
only or candidate-only view in this project is wrapped with.

Every view in this project is function-based, so `role_required` below
is what's actually used throughout accounts/companies/jobs/applications.
`RoleRequiredMixin` is also provided for class-based views, in case you
extend this project with generic views (ListView, CreateView, etc.) —
it isn't used by the current views, but is wired up the same way
LoginRequiredMixin is, so it drops in without surprises.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*roles):
    """
    Decorator for function-based views. Usage:

        @role_required('employer')
        def post_job(request):
            ...

    Requires the user to be authenticated AND have one of the given
    roles; otherwise raises PermissionDenied (rendered as a 403 page).
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied(
                    f"This page is only available to: {', '.join(roles)}."
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


class RoleRequiredMixin:
    """
    Mixin for class-based views. Set `allowed_roles = ['employer']` (or
    similar) on the view class. Combine with django.contrib.auth.mixins
    .LoginRequiredMixin (placed BEFORE this mixin in the MRO) so
    anonymous users get redirected to login rather than hitting a 403
    before they've even had a chance to authenticate.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if self.allowed_roles and request.user.role not in self.allowed_roles:
            raise PermissionDenied(
                f"This page is only available to: {', '.join(self.allowed_roles)}."
            )
        return super().dispatch(request, *args, **kwargs)
