"""Application entry point: uv run uvicorn app.main:app --reload."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.comparison import compare, normalize
from app.exercises import FIRST_EXERCISE, get_exercise

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Tech Speech Trainer", version="0.1.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")

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
        "description": "Вопрос, уточнение и дополнительное условие",
    },
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    """Render the introduction page with levels and the first exercise link."""
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"levels": LEVELS, "first_exercise_id": FIRST_EXERCISE.id},
    )


@app.get(
    "/exercises/{exercise_id}", response_class=HTMLResponse, include_in_schema=False
)
async def exercise_page(request: Request, exercise_id: str):
    """Render an exercise form without revealing the original transcript."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    return templates.TemplateResponse(
        request=request,
        name="exercise.html",
        context={"exercise": exercise, "answer": "", "result": None, "error": None},
    )


@app.post(
    "/exercises/{exercise_id}", response_class=HTMLResponse, include_in_schema=False
)
async def check_answer(
    request: Request,
    exercise_id: str,
    answer: Annotated[str, Form()] = "",
):
    """Validate the answer and render word comparison results or form errors."""
    exercise = get_exercise(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    error = None
    if len(answer) > 2000:
        error = "Ответ слишком длинный. Максимум — 2000 символов."
    elif not normalize(answer):
        error = "Напиши хотя бы одно услышанное слово, затем нажми «Проверить»."
    result = None if error else compare(exercise.transcript, answer)
    return templates.TemplateResponse(
        request=request,
        name="exercise.html",
        context={
            "exercise": exercise,
            "answer": answer[:2000],
            "result": result,
            "error": error,
        },
        status_code=422 if error else 200,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Report application liveness; AI availability is not checked here."""
    return {"status": "ok"}
