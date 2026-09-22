from functools import wraps

from flask import abort, redirect, request, url_for
from flask_login import current_user

from app.models.user import UserRole


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if current_user.role != UserRole.ADMIN:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
