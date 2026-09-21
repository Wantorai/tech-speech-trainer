"""Application entry point: uv run uvicorn app.main:app --reload."""

from dataclasses import asdict
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.comparison import Comparison, Difference, normalize
from app.exercises import EXERCISES, FIRST_EXERCISE, get_exercise, get_next_exercise
from app.feedback import Feedback, build_feedback
from app.history import get_attempt, list_attempts, save_attempt
from app.tutor import ask_tutor
from app.tutor_chat import ask_followup, validate_chat

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Tech Speech Trainer", version="0.1.0")
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
async def home(request: Request):
    """Render the introduction with training levels and catalog entry points."""
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "levels": LEVELS,
            "first_exercise_id": FIRST_EXERCISE.id,
            "exercise_count": len(EXERCISES),
        },
    )


@app.get("/exercises", response_class=HTMLResponse, include_in_schema=False)
async def catalog(request: Request, topic: str = "", level: str = ""):
    """Render available exercises filtered by topic and level without answer text."""
    topics = tuple(dict.fromkeys(exercise.topic for exercise in EXERCISES))
    try:
        selected_level = int(level) if level else None
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Уровень должен быть числом."
        ) from None
    levels = sorted({exercise.level for exercise in EXERCISES})
    selected = [
        exercise
        for exercise in EXERCISES
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
            "total": len(EXERCISES),
        },
    )


@app.get(
    "/exercises/{exercise_id}", response_class=HTMLResponse, include_in_schema=False
)
def exercise_page(request: Request, exercise_id: str, attempt: int | None = None):
    """Render a fresh exercise or restore a saved result after submission."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
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
        context={"exercise": exercise, "answer": "", "result": None, "error": None},
    )


@app.post(
    "/exercises/{exercise_id}", response_class=HTMLResponse, include_in_schema=False
)
def check_answer(
    request: Request,
    exercise_id: str,
    answer: Annotated[str, Form()] = "",
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
        return RedirectResponse(
            str(request.url_for("exercise_page", exercise_id=exercise_id))
            + f"?attempt={attempt_id}#result",
            status_code=303,
            headers={"Cache-Control": "no-store"},
        )
    return templates.TemplateResponse(
        request=request,
        name="exercise.html",
        context={
            "exercise": exercise,
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
