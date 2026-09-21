"use strict";

const aiForm = document.querySelector("#ai-form");
const aiButton = document.querySelector("#ai-button");
const aiStatus = document.querySelector("#ai-status");
const aiAnalysis = document.querySelector("#ai-analysis");
const chat = document.querySelector("#ai-chat");
const chatForm = document.querySelector("#chat-form");
const chatQuestion = document.querySelector("#chat-question");
const chatButton = document.querySelector("#chat-button");
const chatStatus = document.querySelector("#chat-status");
const chatMessages = document.querySelector("#chat-messages");
let initialAnalysis = null;
let chatHistory = [];
let activeRequest = null;

/** Request teaching feedback for the submitted attempt without changing its score. */
async function requestTutor(event) {
  event.preventDefault();
  if (aiButton.disabled || initialAnalysis) return;
  aiButton.disabled = true;
  aiForm.setAttribute("aria-busy", "true");
  aiStatus.textContent = "AI разбирает ответ. Это может занять около минуты; первый запрос бывает дольше…";
  aiAnalysis.replaceChildren();
  const controller = new AbortController();
  activeRequest = controller;
  try {
    const response = await fetch(aiForm.action, {
      method: "POST",
      body: new FormData(aiForm),
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    const data = await response.json();
    if (controller.signal.aborted) return;
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
    if (data.status === "ready") {
      initialAnalysis = data.analysis;
      aiForm.hidden = true;
      chat.hidden = false;
    } else {
      aiButton.textContent = "Попробовать ещё раз";
    }
  } catch {
    if (controller.signal.aborted) return;
    aiStatus.textContent = "Не удалось получить AI-разбор. Результат проверки сохранён. Попробуй позже.";
    aiButton.textContent = "Попробовать ещё раз";
  } finally {
    aiButton.disabled = false;
    aiForm.removeAttribute("aria-busy");
    if (activeRequest === controller) activeRequest = null;
  }
}

/** Append one conversation message as plain text, never as generated HTML. */
function appendChatMessage(label, text) {
  const message = document.createElement("div");
  message.className = "chat-message";
  const author = document.createElement("strong");
  author.textContent = label;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.append(author, paragraph);
  chatMessages.append(message);
}

/** Send a follow-up with the original attempt and the last two successful turns. */
async function sendFollowup(event) {
  event.preventDefault();
  if (chatButton.disabled || !initialAnalysis) return;
  const question = chatQuestion.value.trim();
  if (!question || question.length > 400) {
    chatStatus.textContent = "Введи вопрос от 1 до 400 символов.";
    return;
  }
  const body = new FormData();
  body.set("answer", new FormData(aiForm).get("answer"));
  body.set("question", question);
  body.set("analysis", JSON.stringify(initialAnalysis));
  body.set("history", JSON.stringify(chatHistory));
  const controller = new AbortController();
  activeRequest = controller;
  chatButton.disabled = true;
  chatQuestion.disabled = true;
  chatForm.setAttribute("aria-busy", "true");
  chatStatus.textContent = "Преподаватель отвечает…";
  try {
    const response = await fetch(chatForm.action, {
      method: "POST", body, signal: controller.signal,
      headers: { Accept: "application/json" },
    });
    const data = await response.json();
    if (controller.signal.aborted) return;
    if (!response.ok && response.status !== 429) {
      chatStatus.textContent = data.detail || "Не удалось отправить вопрос.";
      return;
    }
    chatStatus.textContent = data.message;
    if (data.status === "ready") {
      appendChatMessage("Ты", question);
      appendChatMessage("AI-преподаватель", data.reply);
      chatHistory = [...chatHistory, { question, answer_ru: data.reply }].slice(-2);
      chatQuestion.value = "";
    }
  } catch {
    if (controller.signal.aborted) return;
    chatStatus.textContent = "Не удалось получить ответ. Вопрос и переписка сохранены на странице — попробуй ещё раз.";
  } finally {
    chatButton.disabled = false;
    chatQuestion.disabled = false;
    chatForm.removeAttribute("aria-busy");
    if (activeRequest === controller) activeRequest = null;
  }
}

/** Clear ephemeral conversation state when leaving or restoring this page. */
function resetTutorChat() {
  activeRequest?.abort();
  activeRequest = null;
  initialAnalysis = null;
  chatHistory = [];
  chatMessages.replaceChildren();
  aiAnalysis.replaceChildren();
  aiStatus.textContent = "";
  chatStatus.textContent = "";
  chatQuestion.value = "";
  chat.hidden = true;
  aiForm.hidden = false;
  aiButton.disabled = false;
  chatButton.disabled = false;
  chatQuestion.disabled = false;
  aiForm.removeAttribute("aria-busy");
  chatForm.removeAttribute("aria-busy");
  aiButton.textContent = "Спросить AI";
}

if (aiForm) {
  aiForm.addEventListener("submit", requestTutor);
  chatForm.addEventListener("submit", sendFollowup);
  window.addEventListener("pagehide", resetTutorChat);
  aiButton.hidden = false;
}
