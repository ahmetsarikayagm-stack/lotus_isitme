from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Role
from .permissions import can_access


def role_required(*roles):
    """@role_required(Role.ADMIN) — function-based view'lar için."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped

    return decorator


def module_required(module_key: str):
    """@module_required("sales") — permissions.MODULES kaydına göre kontrol."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if can_access(request.user, module_key):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped

    return decorator


admin_required = role_required(Role.ADMIN)
