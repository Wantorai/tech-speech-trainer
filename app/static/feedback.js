"use strict";

const aiForm = document.querySelector("#ai-form");
const aiButton = document.querySelector("#ai-button");
const aiStatus = document.querySelector("#ai-status");
const aiVocabulary = document.querySelector("#ai-vocabulary");

/** Request notes for the submitted attempt while leaving its result visible. */
async function requestVocabulary(event) {
  event.preventDefault();
  if (aiButton.disabled) return;
  aiButton.disabled = true;
  aiForm.setAttribute("aria-busy", "true");
  aiStatus.textContent = "AI готовит пояснения. Первый запрос может занять больше времени…";
  aiVocabulary.replaceChildren();
  try {
    const response = await fetch(aiForm.action, {
      method: "POST",
      body: new FormData(aiForm),
      headers: { Accept: "application/json" },
    });
    const data = await response.json();
    if (!response.ok && response.status !== 429) throw new Error("Request failed");
    aiStatus.textContent = data.message;
    for (const note of data.notes) {
      const word = document.createElement("dt");
      word.lang = "en";
      word.textContent = note.word;
      const meaning = document.createElement("dd");
      meaning.textContent = note.meaning_ru;
      aiVocabulary.append(word, meaning);
    }
    aiButton.textContent = data.status === "ready" ? "Обновить AI-заметки" : "Попробовать ещё раз";
  } catch {
    aiStatus.textContent = "Не удалось получить AI-заметки. Результат проверки сохранён. Попробуй позже.";
    aiButton.textContent = "Попробовать ещё раз";
  } finally {
    aiButton.disabled = false;
    aiForm.removeAttribute("aria-busy");
  }
}

if (aiForm) {
  aiForm.addEventListener("submit", requestVocabulary);
  aiButton.hidden = false;
}
