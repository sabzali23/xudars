from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from curriculum.models import Question, Section, TestKind, Topic
from curriculum.testing import make_child, make_topic
from learning.models import Stage, TestAttempt, TopicProgress, TopicStatus
from learning.services.recommendation import recommend_topic


def answer_all(client, topic, kind, correct_count=None):
    """Проходит тест через интерфейс. correct_count — сколько первых ответов дать верно (None — все)."""
    url = reverse("topic_test", args=[topic.slug, kind])
    answered = 0
    while True:
        response = client.get(url)
        if response.status_code != 200:
            return response
        question = response.context["question"]
        is_correct = correct_count is None or answered < correct_count
        answer = question.correct_index if is_correct else (question.correct_index + 1) % len(question.options)
        response = client.post(url, {"question_id": question.pk, "answer": answer})
        answered += 1
        if response.url != url:
            return response


class CycleTests(TestCase):
    def setUp(self):
        self.child = make_child()
        self.topic = make_topic()
        self.client.force_login(self.child.user)
        self.entry_url = reverse("topic_test", args=[self.topic.slug, "entry"])
        self.final_url = reverse("topic_test", args=[self.topic.slug, "final"])
        self.material_url = reverse("topic_material", args=[self.topic.slug])

    def progress(self):
        return TopicProgress.objects.get(child=self.child, topic=self.topic)

    def finish_first_cycle(self, final_correct=None):
        answer_all(self.client, self.topic, "entry")
        self.client.get(self.material_url)
        return answer_all(self.client, self.topic, "final", correct_count=final_correct)

    # --- Порядок шагов ---

    def test_material_requires_entry_test(self):
        self.assertRedirects(self.client.get(self.material_url), self.entry_url)

    def test_final_test_requires_entry_test(self):
        self.assertRedirects(self.client.get(self.final_url), self.entry_url)
        self.assertFalse(TestAttempt.objects.filter(kind=TestKind.FINAL).exists())

    def test_final_test_requires_opened_material(self):
        answer_all(self.client, self.topic, "entry")
        self.assertRedirects(self.client.get(self.final_url), self.material_url)

    def test_stage_without_finished_entry_test_does_not_skip_it(self):
        TopicProgress.objects.create(
            child=self.child, topic=self.topic, stage=Stage.FINAL_TEST, status=TopicStatus.IN_PROGRESS
        )
        self.assertRedirects(self.client.get(self.material_url), self.entry_url)
        self.assertRedirects(self.client.get(self.final_url), self.entry_url)

    # --- Полный цикл ---

    def test_full_cycle_with_passed_final_test(self):
        response = answer_all(self.client, self.topic, "entry", correct_count=2)
        self.assertRedirects(response, self.material_url, fetch_redirect_response=False)
        progress = self.progress()
        self.assertEqual((progress.status, progress.stage, progress.entry_score), (TopicStatus.IN_PROGRESS, Stage.MATERIAL, 40))

        self.client.get(self.material_url)
        self.assertEqual(self.progress().stage, Stage.FINAL_TEST)

        response = answer_all(self.client, self.topic, "final")
        attempt = TestAttempt.objects.get(kind=TestKind.FINAL)
        result_url = reverse("topic_result", args=[self.topic.slug, attempt.pk])
        self.assertRedirects(response, result_url, fetch_redirect_response=False)
        progress = self.progress()
        self.assertEqual((progress.status, progress.stage, progress.last_score), (TopicStatus.PASSED, Stage.DONE, 100))

        result = self.client.get(result_url)
        self.assertEqual(result.context["before"], 40)
        self.assertEqual(result.context["delta"], 60)
        self.assertEqual(result.context["mistakes"], [])

    def test_low_final_score_needs_repeat_with_new_questions(self):
        self.finish_first_cycle(final_correct=3)
        progress = self.progress()
        self.assertEqual((progress.status, progress.last_score), (TopicStatus.NEEDS_REPEAT, 60))
        first = TestAttempt.objects.get(kind=TestKind.FINAL)
        result = self.client.get(reverse("topic_result", args=[self.topic.slug, first.pk]))
        self.assertEqual(len(result.context["mistakes"]), 2)

        response = self.client.post(reverse("topic_repeat", args=[self.topic.slug]))
        self.assertRedirects(response, self.material_url, fetch_redirect_response=False)
        self.assertEqual((self.progress().status, self.progress().stage), (TopicStatus.IN_PROGRESS, Stage.MATERIAL))

        self.client.get(self.material_url)
        answer_all(self.client, self.topic, "final")
        second = TestAttempt.objects.filter(kind=TestKind.FINAL).order_by("-pk").first()
        final_ids = list(
            Question.objects.filter(topic=self.topic, pool=TestKind.FINAL).order_by("order").values_list("pk", flat=True)
        )
        self.assertEqual(first.question_ids, final_ids[:5])
        self.assertEqual(second.question_ids[:2], final_ids[5:])
        self.assertEqual(self.progress().status, TopicStatus.PASSED)

        result = self.client.get(reverse("topic_result", args=[self.topic.slug, second.pk]))
        self.assertEqual((result.context["before_label"], result.context["before"]), ("Прошлая попытка", 60))

    def test_final_attempts_never_use_entry_questions(self):
        entry_ids = set(Question.objects.filter(pool=TestKind.ENTRY).values_list("pk", flat=True))
        self.finish_first_cycle(final_correct=0)
        self.client.post(reverse("topic_repeat", args=[self.topic.slug]))
        self.client.get(self.material_url)
        answer_all(self.client, self.topic, "final", correct_count=0)

        finals = TestAttempt.objects.filter(kind=TestKind.FINAL)
        self.assertEqual(finals.count(), 2)
        for attempt in finals:
            self.assertFalse(set(attempt.question_ids) & entry_ids)
        self.assertLessEqual(set(TestAttempt.objects.get(kind=TestKind.ENTRY).question_ids), entry_ids)

    # --- Сохранение и возврат ---

    def test_unfinished_test_resumes_from_same_question(self):
        for _ in range(2):
            question = self.client.get(self.entry_url).context["question"]
            self.client.post(self.entry_url, {"question_id": question.pk, "answer": 0})
        response = self.client.get(self.entry_url)
        self.assertEqual(response.context["number"], 3)
        self.assertEqual(TestAttempt.objects.count(), 1)

    def test_resubmitted_answer_is_ignored(self):
        question = self.client.get(self.entry_url).context["question"]
        self.client.post(self.entry_url, {"question_id": question.pk, "answer": question.correct_index})
        self.client.post(self.entry_url, {"question_id": question.pk, "answer": question.correct_index + 1})
        attempt = TestAttempt.objects.get()
        self.assertEqual(attempt.answers, {str(question.pk): question.correct_index})

    def test_answer_is_required(self):
        question = self.client.get(self.entry_url).context["question"]
        response = self.client.post(self.entry_url, {"question_id": question.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["error"])
        self.assertEqual(TestAttempt.objects.get().answers, {})

    # --- Лендинг, каталог и курс ---

    # Список «Скоро» задаём прямо в тесте: в настройках он пустеет по мере появления реальных курсов.
    @override_settings(COMING_SOON_COURSES=["Тестовый предмет"])
    def test_guest_sees_landing_with_signup(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "landing.html")
        self.assertContains(response, reverse("signup"))
        self.assertContains(response, "Тестовый предмет")
        self.assertContains(response, "Скоро")
        # Слайдер историй учеников: по слайду на каждую историю и точка-ссылка на него.
        self.assertEqual(len(response.context["stories"]), len(settings.STUDENT_STORIES))
        for number, story in enumerate(settings.STUDENT_STORIES, start=1):
            self.assertContains(response, f'id="story-{number}"')
            self.assertContains(response, f'href="#story-{number}"')
            self.assertContains(response, story["topic"])
            if story["photo"]:
                self.assertContains(response, story["photo"])

    def test_guest_sees_course_modules_but_not_what_is_inside(self):
        self.client.logout()
        course_url = reverse("course", args=["math"])
        topic_url = reverse("topic", args=[self.topic.slug])
        login_url = f"{reverse('login')}?next={topic_url}"

        # На лендинге карточка ведёт на программу курса и уже показывает названия модулей.
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.topic.section.title)
        self.assertContains(response, course_url)
        self.assertContains(response, self.topic.title)

        # Страница курса открыта гостю: видны модули, но не их содержимое.
        page = self.client.get(course_url)
        self.assertTemplateUsed(page, "learning/course_public.html")
        self.assertContains(page, self.topic.title)
        self.assertContains(page, login_url)

        # Вход в сам модуль — только после авторизации.
        self.assertRedirects(self.client.get(topic_url), login_url, fetch_redirect_response=False)
        self.assertRedirects(
            self.client.get(self.material_url),
            f"{reverse('login')}?next={self.material_url}",
            fetch_redirect_response=False,
        )

    def test_login_returns_parent_to_the_course_they_opened(self):
        self.client.logout()
        course_url = reverse("course", args=["math"])
        response = self.client.post(
            reverse("login"),
            {"username": self.child.user.phone, "password": "test-pass-123", "next": course_url},
        )
        self.assertRedirects(response, course_url, fetch_redirect_response=False)

    def test_catalog_explains_the_method(self):
        """После входа лендинг недоступен, поэтому объяснения должны остаться на экране курсов."""
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Как это работает")
        self.assertContains(response, "Это для родителя")
        self.assertContains(response, "Входной тест")

    @override_settings(COMING_SOON_COURSES=["Тестовый предмет"])
    def test_catalog_shows_course_progress_and_continue(self):
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "learning/catalog.html")
        self.assertContains(response, "Начать")
        self.assertContains(response, "Тестовый предмет")
        self.assertContains(response, "Скоро")

        answer_all(self.client, self.topic, "entry")
        response = self.client.get(reverse("home"))
        course = response.context["sections"][0]
        self.assertTrue(course["started"])
        self.assertEqual(course["recommended"], self.topic)
        self.assertContains(response, "Продолжить")
        self.assertContains(response, reverse("course", args=["math"]))

    def test_course_recommends_topic_in_progress(self):
        answer_all(self.client, self.topic, "entry")
        make_topic("other", order=0)
        response = self.client.get(reverse("course", args=["math"]))
        self.assertEqual(response.context["recommended"], self.topic)
        self.assertContains(response, "Продолжить")

    def test_course_recommendation_ignores_other_courses(self):
        other_section = Section.objects.create(slug="logic", title="Логика", order=2)
        other_topic = Topic.objects.create(section=other_section, slug="logic-1", title="Логика 1", order=1)
        TopicProgress.objects.create(child=self.child, topic=other_topic, status=TopicStatus.IN_PROGRESS)
        response = self.client.get(reverse("course", args=["math"]))
        self.assertEqual(response.context["recommended"], self.topic)

    def test_unknown_course_is_404(self):
        self.assertEqual(self.client.get(reverse("course", args=["nope"])).status_code, 404)

    # --- Доступ ---

    def test_other_parent_cannot_open_result(self):
        self.finish_first_cycle()
        attempt = TestAttempt.objects.get(kind=TestKind.FINAL)
        other = make_child(phone="+992900000002")
        self.client.force_login(other.user)
        response = self.client.get(reverse("topic_result", args=[self.topic.slug, attempt.pk]))
        self.assertEqual(response.status_code, 404)

    def test_progress_page_shows_course_diagram(self):
        self.finish_first_cycle()
        response = self.client.get(reverse("progress"))
        course = response.context["sections"][0]
        self.assertEqual((course["passed"], course["left"], course["percent"]), (1, 0, 100))
        self.assertEqual(course["average"], 100)
        # Кольцевая диаграмма и полосы «было → стало».
        self.assertContains(response, 'class="donut"')
        self.assertContains(response, "tb-fill tb-before")

    def test_progress_page_shows_weak_topics_first(self):
        weak_topic = make_topic("weak", order=2)
        self.finish_first_cycle()
        TopicProgress.objects.create(child=self.child, topic=weak_topic, status=TopicStatus.NEEDS_REPEAT, last_score=20)
        response = self.client.get(reverse("progress"))
        self.assertEqual([p.topic for p in response.context["weak"]], [weak_topic, self.topic])


class RecommendationTests(TestCase):
    def setUp(self):
        self.child = make_child()
        self.t1 = make_topic("t1", order=1)
        self.t2 = make_topic("t2", order=2)
        self.t3 = make_topic("t3", order=3)

    def set_progress(self, topic, status, last_score=None):
        TopicProgress.objects.create(child=self.child, topic=topic, status=status, last_score=last_score)

    def test_new_child_gets_first_topic(self):
        self.assertEqual(recommend_topic(self.child), self.t1)

    def test_unfinished_topic_has_top_priority(self):
        self.set_progress(self.t1, TopicStatus.NEEDS_REPEAT, 20)
        self.set_progress(self.t3, TopicStatus.IN_PROGRESS, 90)
        self.assertEqual(recommend_topic(self.child), self.t3)

    def test_needs_repeat_topic_with_lowest_score(self):
        self.set_progress(self.t1, TopicStatus.PASSED, 90)
        self.set_progress(self.t2, TopicStatus.NEEDS_REPEAT, 60)
        self.set_progress(self.t3, TopicStatus.NEEDS_REPEAT, 30)
        self.assertEqual(recommend_topic(self.child), self.t3)

    def test_then_first_not_started_topic(self):
        self.set_progress(self.t1, TopicStatus.PASSED, 90)
        self.assertEqual(recommend_topic(self.child), self.t2)

    def test_all_passed_returns_weakest(self):
        self.set_progress(self.t1, TopicStatus.PASSED, 95)
        self.set_progress(self.t2, TopicStatus.PASSED, 80)
        self.set_progress(self.t3, TopicStatus.PASSED, 85)
        self.assertEqual(recommend_topic(self.child), self.t2)

    def test_exclude_skips_current_topic(self):
        self.assertEqual(recommend_topic(self.child, exclude=self.t1), self.t2)
