"use strict";

const exerciseAudio = document.querySelector("#exercise-audio");
const replayAudioButton = document.querySelector("#replay-audio");

/** Restart the exercise recording and continue playing from its beginning. */
async function replayExerciseAudio() {
  if (!exerciseAudio) return;
  exerciseAudio.currentTime = 0;
  try {
    await exerciseAudio.play();
  } catch {
    exerciseAudio.focus();
  }
}

replayAudioButton?.addEventListener("click", replayExerciseAudio);
