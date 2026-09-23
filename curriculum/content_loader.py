"""Чтение и проверка контента из папки content/ и запись его в базу.

Структура:
    content/<раздел>/section.json          {"title": ..., "order": ..., "draft": true|false}
    content/<раздел>/topics/<тема>/topic.json
    content/<раздел>/topics/<тема>/summary.md   конспект (читают родитель и ребёнок)
    content/<раздел>/topics/<тема>/guide.md     как провести занятие (для родителя)
Формат topic.json описан в README.md.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import markdown
from django.db import transaction

from .models import Material, Question, Section, TestKind, Topic

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContentError(Exception):
    """Ошибка в файлах контента. В сообщении указан путь к проблемному файлу."""


@dataclass
class QuestionData:
    text: str
    options: list
    correct_index: int
    explanation: str


@dataclass
class TopicData:
    slug: str
    title: str
    order: int
    video_url: str
    summary_md: str
    parent_guide_md: str
    questions: dict


@dataclass
class SectionData:
    slug: str
    title: str
    description: str
    order: int
    draft: bool
    topics: list


def load_content(root, test_size):
    """Проверяет весь контент и только потом записывает его в базу одной транзакцией."""
    sections = read_content(Path(root), test_size)
    write_content(sections)
    return sections


def render_markdown(text):
    return markdown.markdown(text, extensions=["extra", "sane_lists"])


# --- Чтение и проверка ---


def read_content(root, test_size):
    if not root.is_dir():
        raise ContentError(f"{root}: папка с контентом не найдена.")
    section_dirs = sorted(p for p in root.iterdir() if p.is_dir())
    if not section_dirs:
        raise ContentError(f"{root}: нет ни одного раздела.")
    sections = [read_section(d, test_size) for d in section_dirs]

    topic_sections = {}
    for section in sections:
        for topic in section.topics:
            if topic.slug in topic_sections:
                raise ContentError(
                    f"Тема «{topic.slug}» есть в разделах «{topic_sections[topic.slug]}» и «{section.slug}»."
                )
            topic_sections[topic.slug] = section.slug
    return sections


def read_section(section_dir, test_size):
    slug = _check_slug(section_dir)
    path = section_dir / "section.json"
    data = _read_json(path)
    topics_dir = section_dir / "topics"
    if not topics_dir.is_dir():
        raise ContentError(f"{topics_dir}: папка с темами не найдена.")
    topics = [read_topic(d, test_size) for d in sorted(p for p in topics_dir.iterdir() if p.is_dir())]
    if not topics:
        raise ContentError(f"{topics_dir}: в разделе нет ни одной темы.")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise ContentError(f"{path}: поле «description» должно быть строкой.")
    return SectionData(
        slug=slug,
        title=_require_text(data, "title", path),
        description=description.strip(),
        order=_require_int(data, "order", path),
        draft=bool(data.get("draft", False)),
        topics=topics,
    )


def read_topic(topic_dir, test_size):
    slug = _check_slug(topic_dir)
    path = topic_dir / "topic.json"
    data = _read_json(path)

    summary_md = _read_required_markdown(topic_dir / "summary.md", "конспект обязателен и не может быть пустым")
    parent_guide_md = _read_required_markdown(
        topic_dir / "guide.md",
        "руководство для родителя («как провести занятие») обязательно и не может быть пустым",
    )

    video_url = data.get("video_url", "")
    if not isinstance(video_url, str) or (video_url and not video_url.startswith(("http://", "https://"))):
        raise ContentError(f"{path}: «video_url» должен быть пустым или ссылкой, начинающейся с http(s)://.")

    raw_questions = data.get("questions")
    if not isinstance(raw_questions, dict):
        raise ContentError(f"{path}: поле «questions» должно содержать списки «entry» и «final».")
    questions = {}
    for pool in TestKind.values:
        items = raw_questions.get(pool)
        if not isinstance(items, list) or len(items) < test_size:
            raise ContentError(f"{path}: в «questions.{pool}» нужно минимум {test_size} заданий (размер теста).")
        questions[pool] = [_read_question(item, f"{path} → questions.{pool}[{i}]") for i, item in enumerate(items)]
    _check_no_repeated_questions(questions, path)

    return TopicData(
        slug=slug,
        title=_require_text(data, "title", path),
        order=_require_int(data, "order", path),
        video_url=video_url,
        summary_md=summary_md,
        parent_guide_md=parent_guide_md,
        questions=questions,
    )


def _read_required_markdown(path, message):
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text.strip():
        raise ContentError(f"{path}: {message}.")
    return text


def _read_question(item, where):
    if not isinstance(item, dict):
        raise ContentError(f"{where}: задание должно быть JSON-объектом.")
    text = _require_text(item, "text", where)
    options = item.get("options")
    if not isinstance(options, list) or len(options) < 2 or not all(isinstance(o, str) and o.strip() for o in options):
        raise ContentError(f"{where}: «options» должен быть списком минимум из двух непустых строк.")
    correct = item.get("correct")
    if not isinstance(correct, int) or isinstance(correct, bool) or not 0 <= correct < len(options):
        raise ContentError(f"{where}: «correct» — номер правильного варианта от 0 до {len(options) - 1}.")
    explanation = item.get("explanation", "")
    if not isinstance(explanation, str):
        raise ContentError(f"{where}: «explanation» должен быть строкой.")
    return QuestionData(text, [o.strip() for o in options], correct, explanation.strip())


def _check_no_repeated_questions(questions, path):
    """Входной и итоговый тесты должны состоять из разных заданий."""
    seen = {}
    for pool, items in questions.items():
        for i, question in enumerate(items):
            key = " ".join(question.text.lower().split())
            where = f"{pool}[{i}]"
            if key in seen:
                raise ContentError(
                    f"{path}: задание «{question.text}» повторяется ({seen[key]} и {where}). "
                    "Входной и итоговый тесты должны состоять из разных заданий."
                )
            seen[key] = where


def _read_json(path):
    if not path.is_file():
        raise ContentError(f"{path}: файл не найден.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ContentError(f"{path}: некорректный JSON ({error}).") from error
    if not isinstance(data, dict):
        raise ContentError(f"{path}: ожидается JSON-объект.")
    return data


def _check_slug(path):
    if not SLUG_RE.match(path.name):
        raise ContentError(f"{path}: имя папки — только латинские буквы в нижнем регистре, цифры и дефисы.")
    return path.name


def _require_text(data, key, where):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{where}: поле «{key}» должно быть непустой строкой.")
    return value.strip()


def _require_int(data, key, where):
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContentError(f"{where}: поле «{key}» должно быть неотрицательным целым числом.")
    return value


# --- Запись в базу ---


@transaction.atomic
def write_content(sections):
    """Обновляет контент по slug. Темы и прогресс не удаляются; лишние задания в конце пула удаляются."""
    for data in sections:
        section, _ = Section.objects.update_or_create(
            slug=data.slug, defaults={"title": data.title, "description": data.description, "order": data.order}
        )
        for topic_data in data.topics:
            topic, _ = Topic.objects.update_or_create(
                slug=topic_data.slug,
                defaults={"section": section, "title": topic_data.title, "order": topic_data.order},
            )
            Material.objects.update_or_create(
                topic=topic,
                defaults={
                    "video_url": topic_data.video_url,
                    "summary_md": topic_data.summary_md,
                    "summary_html": render_markdown(topic_data.summary_md),
                    "parent_guide_md": topic_data.parent_guide_md,
                    "parent_guide_html": render_markdown(topic_data.parent_guide_md),
                },
            )
            for pool, items in topic_data.questions.items():
                for order, question in enumerate(items):
                    Question.objects.update_or_create(
                        topic=topic,
                        pool=pool,
                        order=order,
                        defaults={
                            "text": question.text,
                            "options": question.options,
                            "correct_index": question.correct_index,
                            "explanation": question.explanation,
                        },
                    )
                Question.objects.filter(topic=topic, pool=pool, order__gte=len(items)).delete()
