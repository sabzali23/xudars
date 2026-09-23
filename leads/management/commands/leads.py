from django.core.management.base import BaseCommand
from django.utils import timezone

from leads.models import ConsultationRequest


class Command(BaseCommand):
    help = "Показывает заявки на консультацию с лендинга (админ-панели в v1 нет)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Показать и уже обработанные заявки.")
        parser.add_argument("--handled", type=int, metavar="ID", help="Отметить заявку с этим номером как обработанную.")

    def handle(self, *args, **options):
        if options["handled"]:
            updated = ConsultationRequest.objects.filter(pk=options["handled"], handled_at__isnull=True).update(
                handled_at=timezone.now()
            )
            self.stdout.write("Заявка отмечена как обработанная." if updated else "Такой необработанной заявки нет.")
            return

        requests = ConsultationRequest.objects.all()
        if not options["all"]:
            requests = requests.filter(handled_at__isnull=True)
        if not requests:
            self.stdout.write("Новых заявок нет.")
            return
        for request in requests:
            mark = "" if request.handled_at is None else "  (обработана)"
            when = timezone.localtime(request.created_at).strftime("%d.%m.%Y %H:%M")
            self.stdout.write(f"#{request.pk}  {when}  {request.name}  {request.get_grade_display()}  {request.phone}{mark}")
        self.stdout.write(f"Всего: {len(requests)}")
