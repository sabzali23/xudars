from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .selection import active_child


def child_required(view):
    """Пускает только родителя с заполненным профилем ребёнка и кладёт активного ребёнка в request.child."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        child = active_child(request)
        if child is None:
            return redirect("child_profile")
        request.child = child
        return view(request, *args, **kwargs)

    return login_required(wrapper)
