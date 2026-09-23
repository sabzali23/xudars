import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from curriculum.content_loader import ContentError, load_content
from curriculum.models import Question, Topic


def question(text, correct=0):
    return {"text": text, "options": ["А", "Б", "В"], "correct": correct, "explanation": "Пояснение"}


def write_topic(
    root,
    slug="fractions",
    entry=5,
    final=6,
    summary="# Конспект\n\nТекст.",
    guide="# Как провести занятие\n\n1. Шаг.",
    **overrides,
):
    section_dir = root / "math"
    topic_dir = section_dir / "topics" / slug
    topic_dir.mkdir(parents=True, exist_ok=True)
    (section_dir / "section.json").write_text(json.dumps({"title": "Математика", "order": 1}), encoding="utf-8")
    data = {
        "title": "Дроби",
        "order": 1,
        "questions": {
            "entry": [question(f"{slug} входное {i}") for i in range(entry)],
            "final": [question(f"{slug} итоговое {i}") for i in range(final)],
        },
        **overrides,
    }
    (topic_dir / "topic.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for name, text in (("summary.md", summary), ("guide.md", guide)):
        if text is not None:
            (topic_dir / name).write_text(text, encoding="utf-8")
    return topic_dir


class LoadContentTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def load(self):
        return load_content(self.root, test_size=5)

    def test_loads_valid_topic(self):
        write_topic(self.root)
        self.load()
        topic = Topic.objects.get(slug="fractions")
        self.assertEqual(topic.questions.filter(pool="entry").count(), 5)
        self.assertEqual(topic.questions.filter(pool="final").count(), 6)
        self.assertIn("<h1>Конспект</h1>", topic.material.summary_html)
        self.assertIn("<h1>Как провести занятие</h1>", topic.material.parent_guide_html)

    def test_reload_keeps_question_ids_and_removes_extra_questions(self):
        write_topic(self.root)
        self.load()
        ids_before = set(Question.objects.values_list("pk", flat=True))
        write_topic(self.root, final=5)
        self.load()
        self.assertEqual(Question.objects.count(), 10)
        self.assertLessEqual(set(Question.objects.values_list("pk", flat=True)), ids_before)

    def test_missing_summary_rejected(self):
        write_topic(self.root, summary=None)
        with self.assertRaisesMessage(ContentError, "конспект обязателен"):
            self.load()
        self.assertFalse(Topic.objects.exists())

    def test_blank_summary_rejected(self):
        write_topic(self.root, summary="  \n\n ")
        with self.assertRaisesMessage(ContentError, "конспект обязателен"):
            self.load()

    def test_missing_parent_guide_rejected(self):
        write_topic(self.root, guide=None)
        with self.assertRaisesMessage(ContentError, "руководство для родителя"):
            self.load()
        self.assertFalse(Topic.objects.exists())

    def test_blank_parent_guide_rejected(self):
        write_topic(self.root, guide="\n  ")
        with self.assertRaisesMessage(ContentError, "руководство для родителя"):
            self.load()

    def test_too_few_questions_rejected(self):
        write_topic(self.root, entry=4)
        with self.assertRaisesMessage(ContentError, "минимум 5 заданий"):
            self.load()

    def test_same_question_in_entry_and_final_rejected(self):
        entry = [question(f"Задание {i}") for i in range(5)]
        final = [question("  задание   0 ")] + [question(f"Итоговое {i}") for i in range(5)]
        write_topic(self.root, questions={"entry": entry, "final": final})
        with self.assertRaisesMessage(ContentError, "разных заданий"):
            self.load()

    def test_correct_index_out_of_range_rejected(self):
        entry = [question(f"Задание {i}", correct=3) for i in range(5)]
        final = [question(f"Итоговое {i}") for i in range(5)]
        write_topic(self.root, questions={"entry": entry, "final": final})
        with self.assertRaisesMessage(ContentError, "«correct»"):
            self.load()

    def test_nothing_written_if_any_topic_invalid(self):
        write_topic(self.root, slug="a-topic")
        write_topic(self.root, slug="b-topic", summary=None)
        with self.assertRaises(ContentError):
            self.load()
        self.assertFalse(Topic.objects.exists())

    def test_repository_content_is_valid(self):
        load_content(settings.CONTENT_DIR, settings.TEST_SIZE)
        self.assertTrue(Topic.objects.exists())
        for topic in Topic.objects.all():
            self.assertTrue(topic.material.summary_md.strip())
            self.assertTrue(topic.material.parent_guide_md.strip())
