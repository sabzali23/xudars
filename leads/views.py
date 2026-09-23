from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from learning.views import landing_context

from .forms import ConsultationForm


@require_POST
def consultation(request):
    """Принимает заявку с лендинга. При ошибке возвращает тот же лендинг с заполненной формой."""
    form = ConsultationForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Заявка принята. Мы свяжемся с вами и подскажем, с чего начать.")
        return redirect("home")
    return render(request, "landing.html", landing_context(form))
