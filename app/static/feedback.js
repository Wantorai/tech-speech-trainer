"use strict";

const aiForm = document.querySelector("#ai-form");
const aiButton = document.querySelector("#ai-button");
const aiStatus = document.querySelector("#ai-status");
const aiAnalysis = document.querySelector("#ai-analysis");

/** Request teaching feedback for the submitted attempt without changing its score. */
async function requestTutor(event) {
  event.preventDefault();
  if (aiButton.disabled) return;
  aiButton.disabled = true;
  aiForm.setAttribute("aria-busy", "true");
  aiStatus.textContent = "AI разбирает ответ. Это может занять около минуты; первый запрос бывает дольше…";
  aiAnalysis.replaceChildren();
  try {
    const response = await fetch(aiForm.action, {
      method: "POST",
      body: new FormData(aiForm),
      headers: { Accept: "application/json" },
    });
    const data = await response.json();
    if (!response.ok && response.status !== 429) throw new Error("Request failed");
    aiStatus.textContent = data.message;
    const sections = [
      ["summary_ru", "Твой ответ"], ["grammar_ru", "Грамматика и смысл"],
      ["listening_ru", "На что обратить внимание на слух"],
      ["example_en", "Похожий пример"], ["example_ru", "Перевод примера"],
    ];
    for (const [key, title] of sections) {
      if (!data.analysis?.[key]) continue;
      const heading = document.createElement("h4");
      heading.textContent = title;
      const text = document.createElement("p");
      text.lang = key === "example_en" ? "en" : "ru";
      text.textContent = data.analysis[key];
      aiAnalysis.append(heading, text);
    }
    aiButton.textContent = data.status === "ready" ? "Спросить AI ещё раз" : "Попробовать ещё раз";
  } catch {
    aiStatus.textContent = "Не удалось получить AI-разбор. Результат проверки сохранён. Попробуй позже.";
    aiButton.textContent = "Попробовать ещё раз";
  } finally {
    aiButton.disabled = false;
    aiForm.removeAttribute("aria-busy");
  }
}

if (aiForm) {
  aiForm.addEventListener("submit", requestTutor);
  aiButton.hidden = false;
}
