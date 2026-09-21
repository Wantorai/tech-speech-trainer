"""Reviewed starter catalog with server-side transcripts and translations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Exercise:
    id: str
    title: str
    topic: str
    level: int
    transcript: str
    translation_ru: str
    audio_file: str


FIRST_EXERCISE = Exercise(
    id="intro-01",
    title="Давайте познакомимся",
    topic="Знакомство и опыт работы",
    level=1,
    transcript=(
        "I work as a frontend developer and build applications for small businesses."
    ),
    audio_file="audio/intro-01.wav",
    translation_ru="Я работаю фронтенд-разработчиком и создаю приложения для малого бизнеса.",
)

EXERCISES = (
    FIRST_EXERCISE,
    Exercise(
        id="intro-02",
        title="Ежедневные задачи",
        topic="Знакомство и опыт работы",
        level=2,
        transcript="I work on the user interface of our main product. My daily tasks include building new features and reviewing changes with other developers.",
        translation_ru="Я работаю над пользовательским интерфейсом нашего основного продукта. Мои ежедневные задачи включают разработку новых функций и проверку изменений вместе с другими разработчиками.",
        audio_file="audio/intro-02.wav",
    ),
    Exercise(
        id="projects-01",
        title="Улучшение продукта",
        topic="Проекты и личный вклад",
        level=1,
        transcript="I improved the search feature to help customers find products faster.",
        translation_ru="Я улучшил функцию поиска, чтобы помочь клиентам быстрее находить товары.",
        audio_file="audio/projects-01.wav",
    ),
    Exercise(
        id="projects-02",
        title="Изменения без перебоев",
        topic="Проекты и личный вклад",
        level=2,
        transcript="Our team replaced a slow service during my last project. I wrote automated tests and helped release the changes without interrupting our customers.",
        translation_ru="Во время моего последнего проекта наша команда заменила медленно работающий сервис. Я написал автоматизированные тесты и помог выпустить изменения, не прерывая работу клиентов.",
        audio_file="audio/projects-02.wav",
    ),
    Exercise(
        id="team-01",
        title="Совместная работа",
        topic="Работа в команде",
        level=1,
        transcript="We review each other's code and discuss important decisions before starting development.",
        translation_ru="Мы проверяем код друг друга и обсуждаем важные решения перед началом разработки.",
        audio_file="audio/team-01.wav",
    ),
    Exercise(
        id="team-02",
        title="Технические разногласия",
        topic="Работа в команде",
        level=2,
        transcript="How do you handle disagreements about technical decisions within your team? Please describe a situation where you helped your colleagues reach an agreement.",
        translation_ru="Как вы справляетесь с разногласиями по техническим решениям в своей команде? Опишите ситуацию, в которой вы помогли коллегам прийти к согласию.",
        audio_file="audio/team-02.wav",
    ),
)


def get_exercise(exercise_id: str) -> Exercise | None:
    """Return the exercise matching the ID, or None if it is unknown."""
    return next(
        (exercise for exercise in EXERCISES if exercise.id == exercise_id), None
    )


def get_next_exercise(exercise_id: str) -> Exercise | None:
    """Return the next catalog exercise without wrapping the final item to the start."""
    for index, exercise in enumerate(EXERCISES[:-1]):
        if exercise.id == exercise_id:
            return EXERCISES[index + 1]
    return None
