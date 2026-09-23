from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from learning.views import _sections_with_progress

from .forms import ChildForm
from .models import Child
from .selection import active_child, children_of, set_active


@login_required
def child_profile(request):
    """Профиль: данные родителя, все дети с их прогрессом и выбор, с кем заниматься."""
    kids = list(children_of(request.user))
    if not kids:
        # Первый вход: на том же адресе показываем форму создания профиля ребёнка.
        return render(
            request,
            "children/child_form.html",
            {"form": ChildForm(), "is_new": True, "action": reverse("child_add")},
        )

    current = active_child(request)
    rows = []
    for kid in kids:
        sections, _ = _sections_with_progress(kid)
        rows.append({"child": kid, "sections": sections, "is_active": kid.pk == current.pk})
    return render(
        request,
        "children/profile.html",
        {"parent": request.user, "rows": rows, "active": current, "is_new": False},
    )


@login_required
def child_add(request):
    """Добавление ребёнка: и первого при регистрации, и следующих из профиля."""
    is_first = not children_of(request.user).exists()
    form = ChildForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        child = form.save(commit=False)
        child.user = request.user
        child.save()
        # Новый ребёнок сразу становится активным: родитель добавил его, чтобы с ним заниматься.
        set_active(request, child)
        messages.success(request, f"Профиль ребёнка «{child.name}» сохранён.")
        return redirect("home" if is_first else "child_profile")
    return render(request, "children/child_form.html", {"form": form, "is_new": is_first})


@login_required
def child_edit(request, pk):
    """Правка данных ребёнка. Чужой ребёнок недоступен: фильтр по родителю в запросе."""
    child = get_object_or_404(Child, pk=pk, user=request.user)
    form = ChildForm(request.POST or None, instance=child)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Данные ребёнка сохранены.")
        return redirect("child_profile")
    return render(request, "children/child_form.html", {"form": form, "child": child, "is_new": False})


@require_POST
@login_required
def child_switch(request, pk):
    """Переключение на другого ребёнка — дальше весь прогресс и рекомендации считаются для него."""
    child = get_object_or_404(Child, pk=pk, user=request.user)
    set_active(request, child)
    messages.success(request, f"Теперь занимается {child.name}.")
    return redirect("home")
