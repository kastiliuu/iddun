document.addEventListener("DOMContentLoaded", () => {
  /* ==========================================================
     SLOT TABS
     ========================================================== */

  const tabs = [
    ...document.querySelectorAll("[data-slot-tab]"),
  ];

  const panels = [
    ...document.querySelectorAll("[data-slot-panel]"),
  ];


  const activateTab = (
    selectedTab,
    {
      focus = false,
    } = {},
  ) => {
    if (!selectedTab) {
      return;
    }

    const target = (
      selectedTab.dataset.slotTab
    );


    tabs.forEach((tab) => {
      const isActive = (
        tab === selectedTab
      );

      tab.classList.toggle(
        "is-active",
        isActive,
      );

      tab.setAttribute(
        "aria-selected",
        String(isActive),
      );

      tab.setAttribute(
        "tabindex",
        isActive
          ? "0"
          : "-1",
      );
    });


    panels.forEach((panel) => {
      const isActive = (
        panel.dataset.slotPanel
        === target
      );

      panel.classList.toggle(
        "is-active",
        isActive,
      );

      panel.hidden = (
        !isActive
      );
    });


    if (focus) {
      selectedTab.focus();
    }
  };


  const moveTabFocus = (
    currentTab,
    direction,
  ) => {
    if (!tabs.length) {
      return;
    }

    const currentIndex = (
      tabs.indexOf(
        currentTab,
      )
    );

    if (currentIndex < 0) {
      return;
    }

    const nextIndex = (
      currentIndex
      + direction
      + tabs.length
    ) % tabs.length;

    activateTab(
      tabs[nextIndex],
      {
        focus: true,
      },
    );
  };


  tabs.forEach((tab) => {
    tab.addEventListener(
      "click",
      () => {
        activateTab(
          tab,
        );
      },
    );


    tab.addEventListener(
      "keydown",
      (event) => {
        switch (event.key) {
          case "ArrowRight":
            event.preventDefault();

            moveTabFocus(
              tab,
              1,
            );

            break;


          case "ArrowLeft":
            event.preventDefault();

            moveTabFocus(
              tab,
              -1,
            );

            break;


          case "Home":
            event.preventDefault();

            activateTab(
              tabs[0],
              {
                focus: true,
              },
            );

            break;


          case "End":
            event.preventDefault();

            activateTab(
              tabs[
                tabs.length - 1
              ],
              {
                focus: true,
              },
            );

            break;


          default:
            break;
        }
      },
    );
  });


  /*
   * Guarantee that the initial state remains consistent even
   * if markup changes or the browser restores focus/state.
   */
  if (tabs.length) {
    const initiallyActive = (
      tabs.find(
        (tab) => (
          tab.getAttribute(
            "aria-selected"
          ) === "true"
        ),
      )
      || tabs[0]
    );

    activateTab(
      initiallyActive,
    );
  }


  /* ==========================================================
     BOOKING HOLD COUNTDOWN
     ========================================================== */

  const hold = (
    document.querySelector(
      "[data-hold-until]"
    )
  );

  const countdown = (
    document.querySelector(
      "[data-hold-countdown]"
    )
  );

  const confirmButton = (
    document.querySelector(
      "[data-confirm-booking]"
    )
  );


  if (
    !hold
    || !countdown
    || !hold.dataset.holdUntil
  ) {
    return;
  }


  const deadline = new Date(
    hold.dataset.holdUntil,
  );


  if (
    Number.isNaN(
      deadline.getTime(),
    )
  ) {
    return;
  }


  const renderCountdown = () => {
    const remaining = Math.max(
      0,
      deadline.getTime()
      - Date.now(),
    );

    const totalSeconds = Math.floor(
      remaining / 1000,
    );

    const minutes = Math.floor(
      totalSeconds / 60,
    );

    const seconds = (
      totalSeconds % 60
    );


    countdown.textContent = (
      `${String(minutes).padStart(2, "0")}:`
      + `${String(seconds).padStart(2, "0")}`
    );


    if (remaining <= 0) {
      countdown.textContent = (
        "Expirado"
      );


      if (confirmButton) {
        confirmButton.disabled = true;

        confirmButton.textContent = (
          "Tempo expirado"
        );
      }


      return false;
    }


    return true;
  };


  if (!renderCountdown()) {
    return;
  }


  const timer = window.setInterval(
    () => {
      if (!renderCountdown()) {
        window.clearInterval(
          timer,
        );
      }
    },
    1000,
  );
});