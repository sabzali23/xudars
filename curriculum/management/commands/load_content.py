from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from curriculum.content_loader import ContentError, load_content


class Command(BaseCommand):
    help = "Проверяет контент (разделы, темы, конспекты, задания) и загружает его в базу."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(settings.CONTENT_DIR), help="Папка с контентом")

    def handle(self, *args, **options):
        try:
            sections = load_content(options["path"], settings.TEST_SIZE)
        except ContentError as error:
            raise CommandError(str(error)) from error

        for section in sections:
            questions = sum(len(items) for topic in section.topics for items in topic.questions.values())
            self.stdout.write(
                self.style.SUCCESS(f"«{section.title}»: тем — {len(section.topics)}, заданий — {questions}.")
            )
            if section.draft:
                self.stdout.write(
                    self.style.WARNING(
                        f"Раздел «{section.title}» помечен как черновик: темы нужно сверить "
                        "с реальной программой вступительного экзамена."
                    )
                )
