"""Рекомендация следующей темы по простому детерминированному правилу (без ML)."""

from curriculum.models import Topic
from learning.models import TopicProgress, TopicStatus


def recommend_topic(child, exclude=None, section=None):
    """Порядок приоритетов (в пределах курса, если передан section):

    1. незавершённая тема (в процессе) — самая недавняя;
    2. тема «нужно повторить» с наименьшим последним баллом;
    3. первая не начатая тема по порядку;
    4. если всё пройдено — тема с наименьшим баллом, для закрепления.
    """
    topics = Topic.objects.order_by("section__order", "order", "id")
    if section is not None:
        topics = topics.filter(section=section)
    topics = [t for t in topics if exclude is None or t.pk != exclude.pk]
    by_id = {t.pk: t for t in topics}
    position = {t.pk: i for i, t in enumerate(topics)}
    progress = [p for p in TopicProgress.objects.filter(child=child) if p.topic_id in by_id]

    def weakest(items):
        return by_id[min(items, key=lambda p: (p.last_score or 0, position[p.topic_id])).topic_id]

    in_progress = [p for p in progress if p.status == TopicStatus.IN_PROGRESS]
    if in_progress:
        return by_id[max(in_progress, key=lambda p: (p.updated_at, p.pk)).topic_id]

    needs_repeat = [p for p in progress if p.status == TopicStatus.NEEDS_REPEAT]
    if needs_repeat:
        return weakest(needs_repeat)

    started = {p.topic_id for p in progress if p.status != TopicStatus.NOT_STARTED}
    for topic in topics:
        if topic.pk not in started:
            return topic

    return weakest(progress) if progress else None
