document.addEventListener("DOMContentLoaded", () => {
  const tabs = [...document.querySelectorAll("[data-slot-tab]")];
  const panels = [...document.querySelectorAll("[data-slot-panel]")];

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.slotTab;
      tabs.forEach((item) => {
        const active = item === tab;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-selected", String(active));
      });
      panels.forEach((panel) => {
        const active = panel.dataset.slotPanel === target;
        panel.classList.toggle("is-active", active);
        panel.hidden = !active;
      });
    });
  });

  const hold = document.querySelector("[data-hold-until]");
  const countdown = document.querySelector("[data-hold-countdown]");
  const confirmButton = document.querySelector("[data-confirm-booking]");
  if (!hold || !countdown || !hold.dataset.holdUntil) return;

  const deadline = new Date(hold.dataset.holdUntil);
  if (Number.isNaN(deadline.getTime())) return;

  const renderCountdown = () => {
    const remaining = Math.max(0, deadline.getTime() - Date.now());
    const totalSeconds = Math.floor(remaining / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    countdown.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    if (remaining <= 0) {
      countdown.textContent = "Expirado";
      if (confirmButton) {
        confirmButton.disabled = true;
        confirmButton.textContent = "Tempo expirado";
      }
      return false;
    }
    return true;
  };

  renderCountdown();
  const timer = window.setInterval(() => {
    if (!renderCountdown()) window.clearInterval(timer);
  }, 1000);
});
