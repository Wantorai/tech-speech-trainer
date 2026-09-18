# Tech Speech Trainer

An English listening practice app for Russian-speaking software developers preparing for technical interviews.

The planned training loop is simple: listen to a short recording, type the English words you heard, and review the differences with AI-assisted explanations in Russian.

## Project status

**Early development — local AI evaluation.** The repository contains a runnable evaluation script, but no training application yet. Application and Docker setup instructions will be added when those workflows are implemented and verified.

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
| AI feedback | Local Qwen3 4B through Ollama, in a separate Python module |
| Audio | Prepared recordings first; text-to-speech integration in a later step |
| Quality checks | pytest, Ruff, and GitHub Actions |
| Packaging | Docker and Docker Compose |

Qwen3 4B through Ollama is selected for the first educational release, with the measured limitations below. The application will compute text differences and accuracy in Python; the model will provide supplementary explanations in Russian. Evaluation of explanations based on precomputed differences is still pending. Text feedback and speech generation are separate capabilities and may use different providers.

The evaluation uses prepared examples covering correct answers, spelling mistakes, omissions, word substitutions, and missing negation. A demo mode without an AI key is still under consideration.

## Run the local AI evaluation

The evaluation uses Python 3.12 or later and the standard library only. It includes 18 synthetic cases: 16 model inputs and two empty inputs that are rejected locally. These are evaluation fixtures, not the planned exercise catalog.

Validate the fixtures and run the offline harness tests from the repository root:

```sh
python scripts/evaluate_local_ai.py --check-only
python -m unittest discover -s tests -v
```

Use the command for your installed interpreter if it differs, such as `python3` or `python3.12`.

To evaluate the model, install Ollama ([Windows instructions](https://docs.ollama.com/windows)) and start its local server. Then download the model and run:

```sh
ollama pull qwen3:4b
python scripts/evaluate_local_ai.py --model qwen3:4b
```

The model download is approximately 2.5 GB; inference needs additional memory. The script connects only to `http://127.0.0.1:11434`, with no API key. Initial downloads require internet access. On a machine with limited memory, close unnecessary applications before evaluating.

Repeat selected cases to inspect consistency:

```sh
python scripts/evaluate_local_ai.py --case exact --case negation --case typo --repeat 2
```

Results are saved incrementally under the ignored `var/evals/` directory. They include model metadata, settings, raw responses, and timings. The script checks the response contract and expected text differences; explanations still require human review. Different but valid grouping of changed words can fail the strict difference check. Exit code zero indicates that requests and response validation completed, not that the model passed a quality assessment.

The experimental prompt accepts equivalent contractions and number spellings. These rules are provisional until the application's text comparison is implemented.

### Initial findings

On September 18, 2026, Qwen3 4B Q4_K_M was evaluated using Ollama 0.34.2 on a Ryzen 5 5500U with 16 GB RAM, using CPU inference, a 2,048-token context, and thinking disabled.

| Measure | Initial prompt | Revised prompt |
| --- | --- | --- |
| Completed responses meeting the output contract | 16/16 | 16/16 |
| Exact expected difference pairs | 6/16 | 9/16 |
| Acceptable feedback after manual review | 7/16 | 12/16 |
| Median request time | 9.1 seconds | 7.6 seconds |
| Maximum request time | 17.5 seconds | 12.8 seconds |

Both runs rejected the two empty inputs without model requests. The revised prompt fixed some reference/answer reversals and recognized the instruction embedded in an answer, but still invented a missing word, missed a spelling mistake, and mishandled an equivalent contraction. It did not reach the initial target of 14 acceptable responses out of 16. The local model is retained for the educational release as a supplementary feedback component; it will not determine the accuracy score.

Manual review accepted some longer quoted spans that failed the strict pair check. This was a small synthetic set reused for prompt revision, not an independent benchmark. The result supports keeping deterministic text comparison separate from AI feedback; it does not establish how this model would perform when explaining precomputed differences.

## Roadmap

- [x] Establish the repository foundation and document the intended scope.
- [x] Evaluate and select a local model, recording quality and latency limitations.
- [ ] Build a minimal Python application and training page.
- [ ] Complete one exercise with audio playback and text comparison.
- [ ] Evaluate explanations of precomputed differences; integrate local AI feedback and handle provider failures.
- [ ] Expand to 24 exercises and save attempt history.
- [ ] Verify Docker setup and add automated checks and screenshots.

## Development notes

The public project overview and setup instructions are maintained in this English README. Personal learning notes are written in Russian under `docs/`, which is intentionally excluded from version control.

Development proceeds in small, reviewable steps. Each step should have a clear outcome, an appropriate verification, and an explanatory commit.
