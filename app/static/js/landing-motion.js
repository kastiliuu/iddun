/* IDDUN landing: small pointer-responsive brand constellation.
   The orbit is decorative, never a functional availability indicator. */
(() => {
  const orbit = document.querySelector("[data-landing-orbit]");
  if (!orbit || window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      !window.matchMedia("(pointer: fine)").matches) return;

  const surface = orbit.closest(".landing-hero__art");
  if (!surface) return;

  surface.addEventListener("pointermove", (event) => {
    const bounds = surface.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const x = ((event.clientX - bounds.left) / bounds.width - .5) * 14;
    const y = ((event.clientY - bounds.top) / bounds.height - .5) * 14;
    orbit.style.setProperty("--orbit-x", `${x}%`);
    orbit.style.setProperty("--orbit-y", `${y}%`);
  }, { passive: true });
  surface.addEventListener("pointerleave", () => {
    orbit.style.setProperty("--orbit-x", "0%");
    orbit.style.setProperty("--orbit-y", "0%");
  });
})();
