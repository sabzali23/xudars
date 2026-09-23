"""Кто из детей занимается сейчас.

У родителя может быть несколько детей. Выбранный ребёнок хранится в сессии, поэтому
экраны занятий не знают о выборе ничего — они получают ребёнка через `child_required`.
"""

from .models import Child

SESSION_KEY = "active_child_id"


def children_of(user):
    """Дети этого родителя, в порядке добавления."""
    return Child.objects.filter(user=user)


def active_child(request):
    """Выбранный ребёнок, а если выбора нет — первый по списку.

    Поиск идёт только среди детей этого родителя, поэтому подменить id в сессии
    и попасть в чужой профиль нельзя.
    """
    kids = children_of(request.user)
    chosen_id = request.session.get(SESSION_KEY)
    if isinstance(chosen_id, int):
        chosen = kids.filter(pk=chosen_id).first()
        if chosen is not None:
            return chosen
    first = kids.first()
    if first is not None:
        set_active(request, first)
    return first


def set_active(request, child):
    request.session[SESSION_KEY] = child.pk
