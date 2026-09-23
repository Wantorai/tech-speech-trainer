"""Application entry point: uv run uvicorn app.main:app --reload."""

from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from app.background import INFERENCE, Generator
from app.comparison import Comparison, Difference, normalize
from app.exercises import (
    EXERCISES,
    FIRST_EXERCISE,
    TOPIC_ORDER,
    get_exercise,
    get_next_exercise,
)
from app.feedback import Feedback, build_feedback
from app.history import get_attempt, list_attempts, save_attempt
from app.library import (
    audio_path,
    choose_exercise,
    cleanup_audio,
    generated_exercises,
    group_state,
    mark_completed,
    protect_exercise,
)
from app.tutor import ask_tutor
from app.tutor_chat import ask_followup, validate_chat

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Recover interrupted audio cleanup and own one background generator per process."""
    await run_in_threadpool(cleanup_audio)
    app.state.generator = Generator()
    try:
        yield
    finally:
        await run_in_threadpool(app.state.generator.close)


app = FastAPI(title="Tech Speech Trainer", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")
AI_LOCK = Lock()
AI_MESSAGES = {
    "ready": "Разбор преподавателя готов.",
    "unavailable": "AI недоступен. Проверь, что Ollama запущена и модель qwen3:4b установлена. Результат проверки сохранён.",
    "timeout": "AI не успел ответить. Можно попробовать позже. Результат проверки сохранён.",
    "invalid_response": "AI вернул ответ неподходящего формата. Результат проверки сохранён.",
    "busy": "AI уже обрабатывает запрос. Попробуй немного позже.",
}

LEVELS = (
    {
        "number": 1,
        "title": "Короткая фраза",
        "description": "1 предложение · 10–15 слов",
    },
    {
        "number": 2,
        "title": "Больше контекста",
        "description": "2 предложения · 20–30 слов",
    },
    {
        "number": 3,
        "title": "Развёрнутая мысль",
        "description": "3–4 предложения · 40–60 слов",
    },
    {
        "number": 4,
        "title": "Как на интервью",
        "description": "60–85 слов · вопрос, уточнение и дополнительное условие",
    },
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    """Render the introduction with training levels and catalog entry points."""
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "levels": LEVELS,
            "first_exercise_id": FIRST_EXERCISE.id,
            "exercise_count": len(EXERCISES) + len(generated_exercises()),
        },
    )


@app.get("/exercises", response_class=HTMLResponse, include_in_schema=False)
def catalog(request: Request, topic: str = "", level: str = ""):
    """Render available exercises filtered by topic and level without answer text."""
    topics = tuple(dict.fromkeys(exercise.topic for exercise in EXERCISES))
    try:
        selected_level = int(level) if level else None
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Уровень должен быть числом."
        ) from None
    levels = sorted({exercise.level for exercise in EXERCISES})
    available = (*EXERCISES, *generated_exercises())
    selected = [
        exercise
        for exercise in available
        if (not topic or exercise.topic == topic)
        and (selected_level is None or exercise.level == selected_level)
    ]
    return templates.TemplateResponse(
        request=request,
        name="catalog.html",
        context={
            "exercises": selected,
            "topics": topics,
            "levels": levels,
            "selected_topic": topic,
            "selected_level": selected_level,
            "total": len(available),
        },
    )


@app.get(
    "/exercises/{exercise_id}", response_class=HTMLResponse, include_in_schema=False
)
def exercise_page(
    request: Request,
    exercise_id: str,
    attempt: int | None = None,
    training: bool = False,
):
    """Render a fresh exercise or restore a saved result after submission."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    if exercise.id.startswith("gen-"):
        protect_exercise(exercise)
    if attempt is not None:
        saved = get_attempt(attempt)
        if saved is None or saved["exercise"]["id"] != exercise_id:
            raise HTTPException(status_code=404, detail="Попытка не найдена")
        if saved["exercise"] != asdict(exercise):
            return RedirectResponse(
                request.url_for("attempt_detail", attempt_id=attempt), status_code=303
            )
        data = saved["feedback"]["comparison"]
        result = Comparison(
            **{
                **data,
                "alignment": tuple(Difference(**item) for item in data["alignment"]),
            }
        )
        feedback = Feedback(
            comparison=result, explanations=tuple(saved["feedback"]["explanations"])
        )
        return templates.TemplateResponse(
            request=request,
            name="exercise.html",
            context={
                "exercise": exercise,
                "training": training,
                "answer": saved["answer"],
                "result": result,
                "feedback": feedback,
                "ai_available": True,
                "next_exercise": get_next_exercise(exercise.id),
                "error": None,
            },
            headers={"Cache-Control": "no-store"},
        )
    return templates.TemplateResponse(
        request=request,
        name="exercise.html",
        context={
            "exercise": exercise,
            "answer": "",
            "result": None,
            "error": None,
            "training": training,
        },
    )


@app.post(
    "/exercises/{exercise_id}", response_class=HTMLResponse, include_in_schema=False
)
def check_answer(
    request: Request,
    exercise_id: str,
    answer: Annotated[str, Form()] = "",
    training: bool = False,
):
    """Validate and save an answer, then redirect to its result or render errors."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    error = None
    if len(answer) > 2000:
        error = "Ответ слишком длинный. Максимум — 2000 символов."
    elif not normalize(answer):
        error = "Напиши хотя бы одно услышанное слово, затем нажми «Проверить»."
    feedback = None if error else build_feedback(exercise.transcript, answer)
    result = feedback.comparison if feedback else None
    if feedback is not None:
        attempt_id = save_attempt(exercise, answer, feedback)
        mark_completed(exercise.id)
        return RedirectResponse(
            str(request.url_for("exercise_page", exercise_id=exercise_id))
            + f"?attempt={attempt_id}"
            + ("&training=1" if training else "")
            + "#result",
            status_code=303,
            headers={"Cache-Control": "no-store"},
        )
    return templates.TemplateResponse(
        request=request,
        name="exercise.html",
        context={
            "exercise": exercise,
            "training": training,
            "answer": answer[:2000],
            "result": result,
            "feedback": feedback,
            "ai_available": result is not None,
            "next_exercise": get_next_exercise(exercise.id),
            "error": error,
        },
        status_code=422 if error else 200,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/history", response_class=HTMLResponse, include_in_schema=False)
def history_page(request: Request, page: Annotated[int, Query(ge=1, le=1000000)] = 1):
    """Render a paginated list of locally saved attempts."""
    attempts, has_next = list_attempts(page)
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"attempts": attempts, "page": page, "has_next": has_next},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/history/{attempt_id}", response_class=HTMLResponse, include_in_schema=False)
def attempt_detail(request: Request, attempt_id: int):
    """Show the original saved answer and feedback without running AI or rescoring."""
    attempt = get_attempt(attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Попытка не найдена")
    return templates.TemplateResponse(
        request=request,
        name="attempt.html",
        context={
            "attempt": attempt,
            "current_exercise": get_exercise(attempt["exercise"]["id"]),
        },
        headers={"Cache-Control": "no-store"},
    )


@app.post("/exercises/{exercise_id}/ai", include_in_schema=False)
def ai_notes(exercise_id: str, answer: Annotated[str, Form()] = ""):
    """Fetch tutor analysis in a worker thread without queueing concurrent inference."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    if len(answer) > 2000 or not normalize(answer):
        raise HTTPException(
            status_code=422, detail="Отправь допустимый ответ на упражнение."
        )
    if not AI_LOCK.acquire(blocking=False):
        return JSONResponse(
            {"status": "busy", "message": AI_MESSAGES["busy"], "analysis": None},
            status_code=429,
            headers={"Cache-Control": "no-store"},
        )
    try:
        with INFERENCE.use(teacher=True):
            feedback = ask_tutor(exercise, answer)
    finally:
        AI_LOCK.release()
    return JSONResponse(
        {
            "status": feedback.status,
            "message": AI_MESSAGES[feedback.status],
            "analysis": feedback.analysis,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.post("/exercises/{exercise_id}/ai/chat", include_in_schema=False)
def ai_chat(
    exercise_id: str,
    answer: Annotated[str, Form()] = "",
    question: Annotated[str, Form()] = "",
    analysis: Annotated[str, Form()] = "",
    history: Annotated[str, Form()] = "[]",
):
    """Answer a contextual follow-up without persisting the conversation."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    if len(answer) > 2000 or not normalize(answer):
        raise HTTPException(
            status_code=422, detail="Отправь допустимый ответ на упражнение."
        )
    try:
        parsed_analysis, parsed_history = validate_chat(question, analysis, history)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    if not AI_LOCK.acquire(blocking=False):
        return JSONResponse(
            {"status": "busy", "message": AI_MESSAGES["busy"]},
            status_code=429,
            headers={"Cache-Control": "no-store"},
        )
    try:
        with INFERENCE.use(teacher=True):
            result = ask_followup(
                exercise, answer, question, parsed_analysis, parsed_history
            )
    finally:
        AI_LOCK.release()
    return JSONResponse(
        {
            "status": result.status,
            "message": "Ответ готов."
            if result.status == "ready"
            else AI_MESSAGES[result.status],
            "reply": result.analysis["answer_ru"] if result.analysis else None,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Report application liveness; AI availability is not checked here."""
    return {"status": "ok"}


@app.post("/train", include_in_schema=False)
def train(
    request: Request,
    topic: Annotated[str, Form()] = "",
    level: Annotated[str, Form()] = "",
):
    """Select an immediate training item and request at most one background successor."""
    topic = topic or TOPIC_ORDER[0]
    try:
        selected_level = int(level or "1")
    except ValueError:
        raise HTTPException(422, "Некорректный уровень") from None
    if topic not in TOPIC_ORDER or selected_level not in range(1, 5):
        raise HTTPException(422, "Неизвестная тема или уровень")
    exercise = choose_exercise(topic, selected_level)
    request.app.state.generator.request(topic, selected_level)
    return RedirectResponse(
        str(request.url_for("exercise_page", exercise_id=exercise.id)) + "?training=1",
        status_code=303,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/training-status", include_in_schema=False)
def training_status(topic: str, level: int):
    """Expose preparation status without starting jobs or revealing exercise answers."""
    if topic not in TOPIC_ORDER or level not in range(1, 5):
        raise HTTPException(422, "Неизвестная тема или уровень")
    return JSONResponse(
        {"status": group_state(topic, level)["status"]},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/generated-audio/{identifier}.wav", include_in_schema=False)
def generated_audio(identifier: str):
    """Serve only published generated audio while hiding staging and unrelated files."""
    exercise = get_exercise(identifier)
    if exercise is None or not identifier.startswith("gen-"):
        raise HTTPException(404, "Аудио не найдено")
    try:
        path = audio_path(identifier)
    except ValueError:
        raise HTTPException(404, "Аудио не найдено") from None
    if not path.is_file():
        raise HTTPException(404, "Аудио не найдено")
    return FileResponse(path, media_type="audio/wav")
