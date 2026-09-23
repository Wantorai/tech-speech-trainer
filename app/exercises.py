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
    Exercise(
        id="intro-03",
        title="Работа с дизайнером",
        topic="Знакомство и опыт работы",
        level=1,
        transcript="I usually discuss new features with our designer before writing any code.",
        translation_ru="Обычно я обсуждаю новые функции с нашим дизайнером, прежде чем писать код.",
        audio_file="audio/intro-03.wav",
    ),
    Exercise(
        id="intro-04",
        title="Первый опыт",
        topic="Знакомство и опыт работы",
        level=2,
        transcript="I started my career by fixing small bugs in existing applications. Over time, I became responsible for developing complete features and supporting them.",
        translation_ru="Я начал свою карьеру с исправления небольших ошибок в существующих приложениях. Со временем я стал отвечать за разработку целых функций и их поддержку.",
        audio_file="audio/intro-04.wav",
    ),
    Exercise(
        id="intro-05",
        title="Как устроена моя работа",
        topic="Знакомство и опыт работы",
        level=3,
        transcript="I have been working on the same product for almost two years. Our team builds tools that help small companies manage their orders. I mainly develop user interfaces, but I also investigate issues reported by customers and discuss possible solutions with backend developers.",
        translation_ru="Я работаю над одним и тем же продуктом почти два года. Наша команда создаёт инструменты, которые помогают небольшим компаниям управлять заказами. В основном я разрабатываю пользовательские интерфейсы, но также разбираюсь с проблемами, о которых сообщают клиенты, и обсуждаю возможные решения с бэкенд-разработчиками.",
        audio_file="audio/intro-05.wav",
    ),
    Exercise(
        id="intro-06",
        title="Освоение незнакомого кода",
        topic="Знакомство и опыт работы",
        level=3,
        transcript="When I joined my current team, I was unfamiliar with most of the codebase. I began by reading tests and asking colleagues to explain important decisions. After a few weeks, I could make small changes independently and explain how they affected other parts of the application.",
        translation_ru="Когда я присоединился к нынешней команде, большая часть кодовой базы была мне незнакома. Я начал с чтения тестов и просил коллег объяснять важные решения. Через несколько недель я уже мог самостоятельно вносить небольшие изменения и объяснять, как они влияют на другие части приложения.",
        audio_file="audio/intro-06.wav",
    ),
    Exercise(
        id="intro-07",
        title="Опыт для новой команды",
        topic="Знакомство и опыт работы",
        level=4,
        transcript="Could you walk me through your current role and explain which parts of your experience would be most useful to a team building a new product? Please distinguish between tasks you completed independently and decisions that were made together with more experienced colleagues. Assume that our team uses a different programming language, so focus on the skills you could bring rather than specific tools.",
        translation_ru="Не могли бы вы рассказать о своей нынешней роли и объяснить, какой ваш опыт был бы наиболее полезен команде, создающей новый продукт? Пожалуйста, разграничьте задачи, которые вы выполняли самостоятельно, и решения, принятые вместе с более опытными коллегами. Предположим, наша команда использует другой язык программирования, поэтому сосредоточьтесь на навыках, которые вы могли бы применить, а не на конкретных инструментах.",
        audio_file="audio/intro-07.wav",
    ),
    Exercise(
        id="intro-08",
        title="Обучение под срок",
        topic="Знакомство и опыт работы",
        level=4,
        transcript="Can you describe a time when you had to learn an unfamiliar technology quickly while still being responsible for delivering a feature on schedule? Explain how you decided what to study first and how you checked that your understanding was sufficient for the task. In your answer, assume that you could not ask a senior developer for help during the first two days.",
        translation_ru="Можете описать случай, когда вам пришлось быстро освоить незнакомую технологию и при этом вы отвечали за выпуск функции в срок? Объясните, как вы решали, что изучать в первую очередь, и как проверяли, что ваших знаний достаточно для задачи. Отвечая, исходите из того, что в первые два дня вы не могли обратиться за помощью к старшему разработчику.",
        audio_file="audio/intro-08.wav",
    ),
    Exercise(
        id="projects-03",
        title="Проверка формы",
        topic="Проекты и личный вклад",
        level=1,
        transcript="I added validation to prevent users from submitting incomplete registration forms.",
        translation_ru="Я добавил проверку данных, чтобы пользователи не могли отправлять незаполненные до конца формы регистрации.",
        audio_file="audio/projects-03.wav",
    ),
    Exercise(
        id="projects-04",
        title="Оценка результата",
        topic="Проекты и личный вклад",
        level=2,
        transcript="We measured page loading times before changing the image delivery process. After the release, we checked the same measurements to confirm the improvement.",
        translation_ru="Мы измерили время загрузки страниц, прежде чем менять процесс доставки изображений. После выпуска изменений мы повторили те же измерения, чтобы подтвердить улучшение.",
        audio_file="audio/projects-04.wav",
    ),
    Exercise(
        id="projects-05",
        title="Поиск причины замедления",
        topic="Проекты и личный вклад",
        level=3,
        transcript="A customer reported that the dashboard became slow after several minutes of use. I reproduced the problem and found that we were keeping unnecessary data in memory. After fixing the issue, I added a test and asked a teammate to review the change before release.",
        translation_ru="Клиент сообщил, что через несколько минут работы панель управления начинала тормозить. Я воспроизвёл проблему и обнаружил, что мы хранили в памяти ненужные данные. Исправив проблему, я добавил тест и попросил коллегу проверить изменение перед выпуском.",
        audio_file="audio/projects-05.wav",
    ),
    Exercise(
        id="projects-06",
        title="Не всё сразу",
        topic="Проекты и личный вклад",
        level=3,
        transcript="Our original plan included several improvements to the payment flow, but the deadline was approaching. We agreed to release the most important change first and postpone the rest. I documented the remaining work so that another developer could continue without repeating our investigation.",
        translation_ru="Наш первоначальный план включал несколько улучшений процесса оплаты, но срок сдачи приближался. Мы договорились сначала выпустить самое важное изменение, а остальные отложить. Я описал оставшуюся работу, чтобы другой разработчик мог продолжить её, не повторяя наше исследование.",
        audio_file="audio/projects-06.wav",
    ),
    Exercise(
        id="projects-07",
        title="Измеримый личный вклад",
        topic="Проекты и личный вклад",
        level=4,
        transcript="Could you describe a project where your own contribution made a measurable difference to the product, and explain how you separated that impact from other changes? Please include the evidence you collected before and after the release, rather than only describing the code you wrote. If reliable measurements were unavailable, explain what you would use instead and what limitations you would mention to the team.",
        translation_ru="Не могли бы вы описать проект, в котором ваш личный вклад привёл к измеримым изменениям в продукте, и объяснить, как вы отделили этот эффект от влияния других изменений? Пожалуйста, расскажите о данных, собранных до и после выпуска, а не только о написанном коде. Если надёжных измерений не было, объясните, что вы использовали бы вместо них и о каких ограничениях предупредили бы команду.",
        audio_file="audio/projects-07.wav",
    ),
    Exercise(
        id="projects-08",
        title="Выпуск с ограничениями",
        topic="Проекты и личный вклад",
        level=4,
        transcript="How would you approach releasing a change to a service that handles customer orders if the current implementation has very few automated tests and limited documentation? Explain how you would identify the most important risks and decide whether the change was ready for production. Assume that you cannot stop the service during the release and must be able to restore the previous behavior quickly.",
        translation_ru="Как бы вы подошли к выпуску изменения в сервисе обработки заказов клиентов, если в текущей реализации очень мало автоматизированных тестов и недостаточно документации? Объясните, как вы выявили бы самые важные риски и определили, готово ли изменение к работе в промышленной среде. Предположим, вы не можете остановить сервис во время выпуска и должны иметь возможность быстро вернуть прежнее поведение.",
        audio_file="audio/projects-08.wav",
    ),
    Exercise(
        id="team-03",
        title="Обсуждение требований",
        topic="Работа в команде",
        level=1,
        transcript="I ask questions early when a task description leaves important details unclear.",
        translation_ru="Я задаю вопросы заранее, если в описании задачи остаются неясными важные детали.",
        audio_file="audio/team-03.wav",
    ),
    Exercise(
        id="team-04",
        title="Почему выбран этот подход",
        topic="Работа в команде",
        level=2,
        transcript="A colleague suggested a simpler approach during our code review. I asked about the tradeoffs before updating my implementation and explaining the changes.",
        translation_ru="Во время проверки кода коллега предложил более простой подход. Я спросил о его преимуществах и недостатках, прежде чем обновить свою реализацию и объяснить изменения.",
        audio_file="audio/team-04.wav",
    ),
    Exercise(
        id="team-05",
        title="Уточнение ожиданий",
        topic="Работа в команде",
        level=3,
        transcript="We discovered that two developers had interpreted the same requirement differently. Instead of choosing one interpretation immediately, we met with the product manager to clarify the expected behavior. We then updated the task description and added examples to prevent the same misunderstanding in future work.",
        translation_ru="Мы обнаружили, что два разработчика по-разному поняли одно и то же требование. Вместо того чтобы сразу выбрать одну трактовку, мы встретились с менеджером продукта и уточнили ожидаемое поведение. Затем мы обновили описание задачи и добавили примеры, чтобы избежать такого же недопонимания в дальнейшей работе.",
        audio_file="audio/team-05.wav",
    ),
    Exercise(
        id="team-06",
        title="Предупредить о задержке",
        topic="Работа в команде",
        level=3,
        transcript="I realized that my task would take longer than I had estimated because an external service behaved differently from its documentation. I informed the team as soon as I understood the problem. Together, we adjusted the plan and agreed on a smaller change that we could deliver safely.",
        translation_ru="Я понял, что моя задача займёт больше времени, чем я предполагал, потому что внешний сервис работал не так, как было описано в документации. Я сообщил команде, как только разобрался в проблеме. Вместе мы скорректировали план и договорились о меньшем изменении, которое могли выпустить без лишнего риска.",
        audio_file="audio/team-06.wav",
    ),
    Exercise(
        id="team-07",
        title="Разногласие перед выпуском",
        topic="Работа в команде",
        level=4,
        transcript="How would you handle a disagreement with a colleague who wants to rewrite a working component while you believe a smaller change would solve the immediate problem? Please explain how you would compare the alternatives and keep the discussion focused on the needs of the product. Assume that the release is scheduled for next week and neither of you has authority to make the final decision alone.",
        translation_ru="Как бы вы разрешили разногласие с коллегой, который хочет переписать работающий компонент, тогда как вы считаете, что небольшое изменение решит текущую проблему? Пожалуйста, объясните, как вы сравнили бы варианты и удержали обсуждение в рамках потребностей продукта. Предположим, выпуск запланирован на следующую неделю и ни один из вас не вправе единолично принять окончательное решение.",
        audio_file="audio/team-07.wav",
    ),
    Exercise(
        id="team-08",
        title="Передача незавершённой задачи",
        topic="Работа в команде",
        level=4,
        transcript="What would you include in a handover when another developer needs to continue your unfinished task and you will be unavailable for the next several days? Explain how you would communicate the current state, the decisions already made, and the questions that still need investigation. Assume that the other developer is unfamiliar with this part of the application and has only an hour to prepare.",
        translation_ru="Что бы вы включили в передачу задачи, если другому разработчику нужно продолжить вашу незавершённую работу, а вы будете недоступны несколько дней? Объясните, как вы сообщили бы о текущем состоянии, уже принятых решениях и вопросах, которые ещё предстоит исследовать. Предположим, этот разработчик не знаком с данной частью приложения и у него есть только час на подготовку.",
        audio_file="audio/team-08.wav",
    ),
)

TOPIC_ORDER = tuple(dict.fromkeys(exercise.topic for exercise in EXERCISES))
EXERCISES = tuple(
    sorted(
        EXERCISES,
        key=lambda exercise: (
            TOPIC_ORDER.index(exercise.topic),
            exercise.level,
            exercise.id,
        ),
    )
)


def get_exercise(exercise_id: str) -> Exercise | None:
    """Find a prepared or generated exercise without exposing absent records."""
    if exercise_id.startswith("gen-"):
        from app.library import find_generated

        return find_generated(exercise_id)
    return next(
        (exercise for exercise in EXERCISES if exercise.id == exercise_id), None
    )


def get_next_exercise(exercise_id: str) -> Exercise | None:
    """Return the next catalog exercise without wrapping the final item to the start."""
    for index, exercise in enumerate(EXERCISES[:-1]):
        if exercise.id == exercise_id:
            return EXERCISES[index + 1]
    return None
