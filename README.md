# Tech Speech Trainer

An English listening practice app for Russian-speaking software developers preparing for technical interviews.

The planned training loop is simple: listen to a short recording, type the English words you heard, and review the differences with AI-assisted explanations in Russian.

## Project status

**Early development — repository foundation only.** There is no runnable application yet. Local and Docker setup instructions will be added when those workflows are implemented and verified.

This is a learning project focused on Python development, practical AI integration, and a reproducible setup for reviewers.

## Planned learning experience

1. Choose a topic and difficulty level.
2. Listen to an English recording, replaying it as needed.
3. Type what you heard in English.
4. Review the original transcript, missing or substituted words, and possible spelling mistakes.
5. Read explanations in Russian and continue to the next exercise.

Text comparison will provide a reproducible measure of transcription accuracy. AI will explain differences and vocabulary. Written answers alone cannot reliably distinguish a typing mistake from a listening mistake, so feedback will acknowledge that uncertainty.

| Level | Exercise length |
| --- | --- |
| 1 | One sentence, 10–15 words |
| 2 | Two sentences, 20–30 words |
| 3 | Three or four sentences, 40–60 words |
| 4 | An extended interview question with a follow-up and an additional condition |

Initial topics will cover introductions and responsibilities, previous projects and personal contributions, and teamwork. Later topics will include debugging, testing, APIs, databases, releases, and technical decisions.

## First release scope

- A single local user, without registration.
- Russian interface and feedback, with English recordings and transcripts.
- A reviewed set of 24 exercises: three topics, four levels, two exercises per combination.
- Saved audio files for repeated playback.
- Text comparison and AI-assisted feedback.
- Local attempt history.
- Verified local and Docker launch instructions.

## Planned implementation

| Area | Technology or approach |
| --- | --- |
| Backend | Python and FastAPI |
| Interface | Jinja2 templates, HTML, CSS, and a small amount of JavaScript |
| Storage | SQLite |
| AI feedback | A separate Python module; provider selection pending evaluation |
| Audio | Prepared recordings first; text-to-speech integration in a later step |
| Quality checks | pytest, Ruff, and GitHub Actions |
| Packaging | Docker and Docker Compose |

We will evaluate a small local model through Ollama for response quality and latency before choosing the first AI provider. A paid API remains an option. Text feedback and speech generation are separate capabilities and may use different providers.

The initial experiment will use prepared examples covering correct answers, spelling mistakes, omissions, word substitutions, and missing negation. A demo mode without an AI key is still under consideration.

## Roadmap

- [x] Establish the repository foundation and document the intended scope.
- [ ] Evaluate a local AI model and select the first feedback provider.
- [ ] Build a minimal Python application and training page.
- [ ] Complete one exercise with audio playback and text comparison.
- [ ] Add validated AI feedback and handle provider failures.
- [ ] Expand to 24 exercises and save attempt history.
- [ ] Verify Docker setup and add automated checks and screenshots.

## Development notes

The public project overview and setup instructions are maintained in this English README. Personal learning notes are written in Russian under `docs/`, which is intentionally excluded from version control.

Development proceeds in small, reviewable steps. Each step should have a clear outcome, an appropriate verification, and an explanatory commit.
