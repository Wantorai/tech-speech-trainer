"use strict";

const trainingStatus = document.querySelector("#training-status");
let trainingTimer;
let trainingStopped = false;
const preparationMessages = {
  generating: "Preparing a new exercise in the background. You can keep practising.",
  ready: "The next exercise is ready.",
  unavailable: "The new exercise is not available yet. The next one will come from the library.",
  full: "This group has enough uncompleted exercises. We will continue from the library.",
  idle: "The next exercise will be selected from the library without waiting.",
};

/** Poll preparation status without triggering new generation requests. */
async function refreshTrainingStatus() {
  if (trainingStopped || !trainingStatus) return;
  try {
    const response = await fetch(trainingStatus.dataset.url, {cache: "no-store"});
    if (!response.ok) throw new Error("Status unavailable");
    const data = await response.json();
    const icon = trainingStatus.querySelector(".status-icon");
    const text = trainingStatus.querySelector(".training-status-text");
    if (icon) {
      icon.textContent = data.status === "ready" ? "✓" : "◷";
      icon.className = `status-icon status-icon--${data.status === "ready" ? "ready" : "working"}`;
    }
    if (text) text.textContent = preparationMessages[data.status] || preparationMessages.idle;
  } catch {
    trainingStatus.querySelector(".training-status-text").textContent = "The next exercise is available from the library.";
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
