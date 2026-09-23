"""Хелперы для автотестов: создают тему с заданиями и родителя с ребёнком."""

from accounts.models import User
from children.models import Child

from .models import Material, Question, Section, TestKind, Topic


def make_topic(slug="fractions", order=1, entry=5, final=7):
    section, _ = Section.objects.get_or_create(slug="math", defaults={"title": "Математика"})
    topic = Topic.objects.create(section=section, slug=slug, title=slug.title(), order=order)
    Material.objects.create(
        topic=topic,
        summary_md="# Конспект",
        summary_html="<h1>Конспект</h1>",
        parent_guide_md="# Как провести занятие",
        parent_guide_html="<h1>Как провести занятие</h1>",
    )
    for pool, count in ((TestKind.ENTRY, entry), (TestKind.FINAL, final)):
        for i in range(count):
            Question.objects.create(
                topic=topic, pool=pool, order=i, text=f"{slug} {pool} {i}", options=["А", "Б", "В"], correct_index=0
            )
    return topic


def make_child(phone="+992900000001"):
    user = User.objects.create_user(phone=phone, password="test-pass-123", name="Родитель")
    return Child.objects.create(user=user, name="Али", grade=4, target_school="Школа")
