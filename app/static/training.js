"use strict";

const trainingStatus = document.querySelector("#training-status");
let trainingTimer;
let trainingStopped = false;
const preparationMessages = {
  generating: "Готовим новое упражнение в фоне. Можно продолжать заниматься.",
  ready: "Новое упражнение готово — получишь его на следующем ходе.",
  unavailable: "Новое упражнение пока не удалось подготовить. Следующее возьмём из библиотеки.",
  full: "В этой группе достаточно непройденных заданий. Продолжаем из библиотеки.",
  idle: "Следующее упражнение выберем из библиотеки без ожидания.",
};

/** Poll preparation status without triggering new generation requests. */
async function refreshTrainingStatus() {
  if (trainingStopped || !trainingStatus) return;
  try {
    const response = await fetch(trainingStatus.dataset.url, {cache: "no-store"});
    if (!response.ok) throw new Error("Status unavailable");
    const data = await response.json();
    trainingStatus.textContent = preparationMessages[data.status] || preparationMessages.idle;
  } catch {
    trainingStatus.textContent = "Следующее упражнение доступно из библиотеки.";
  }
  if (!trainingStopped) trainingTimer = setTimeout(refreshTrainingStatus, 4000);
}

/** Stop status polling when the training document is left. */
function stopTrainingStatus() {
  trainingStopped = true;
  clearTimeout(trainingTimer);
}

window.addEventListener("pagehide", stopTrainingStatus);
refreshTrainingStatus();
