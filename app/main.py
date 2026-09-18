"""Application entry point: uv run uvicorn app.main:app --reload."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"levels": LEVELS},
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Report application liveness; AI availability is not checked here."""
    return {"status": "ok"}
