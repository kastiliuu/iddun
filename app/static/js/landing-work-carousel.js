"use strict";

(() => {
  const track = document.querySelector("[data-work-carousel]");
  if (!track) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  document.querySelectorAll("[data-work-direction]").forEach((button) => {
    button.addEventListener("click", () => {
      const firstCard = track.querySelector(".landing-work-card");
      if (!firstCard) return;
      const step = firstCard.getBoundingClientRect().width
        + parseFloat(getComputedStyle(track).columnGap || "0");
      const direction = Number(button.dataset.workDirection);
      track.scrollBy({
        left: direction * step,
        behavior: reduceMotion.matches ? "instant" : "smooth",
      });
    });
  });
})();
