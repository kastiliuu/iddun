(() => {
  'use strict';

  /* ==========================================================
     IDDUN — HOME INTERACTIONS
     ========================================================== */

  const prefersReducedMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  );

  const prefersCoarsePointer = window.matchMedia(
    '(pointer: coarse)'
  );

  const reducedMotion = prefersReducedMotion.matches;

  /*
   * Temporary local persistence.
   *
   * Favorites will later be migrated to the real IDDUN API.
   * Keep the current key so existing local prototype favorites
   * are not unnecessarily discarded.
   */
  const FAVORITES_KEY = 'iddun:favorites:v2';


  /* ==========================================================
     HELPERS
     ========================================================== */

  const normalize = (value) =>
    String(value ?? '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLocaleLowerCase('pt-BR')
      .trim();


  const parseStoredArray = (value) => {
    try {
      const parsed = JSON.parse(value || '[]');

      return Array.isArray(parsed)
        ? parsed
        : [];
    } catch (_) {
      return [];
    }
  };


  /* ==========================================================
     FAVORITES
     ========================================================== */

  const storedFavorites = parseStoredArray(
    window.localStorage.getItem(
      FAVORITES_KEY
    )
  );

  const favorites = new Set(
    storedFavorites.filter(Boolean)
  );


  const persistFavorites = () => {
    try {
      window.localStorage.setItem(
        FAVORITES_KEY,
        JSON.stringify([
          ...favorites,
        ])
      );
    } catch (_) {
      /*
       * Storage can be unavailable in private browsing or
       * restricted environments. The interaction must still
       * work during the current page session.
       */
    }
  };


  const syncFavorite = (
    button,
    active
  ) => {
    const name =
      button.dataset.favoriteName ||
      'item';

    button.dataset.active =
      String(active);

    button.setAttribute(
      'aria-pressed',
      String(active)
    );

    button.setAttribute(
      'aria-label',
      active
        ? `Remover ${name} dos favoritos`
        : `Favoritar ${name}`
    );
  };


  const animateFavorite = (
    button
  ) => {
    if (reducedMotion) {
      return;
    }

    button.classList.remove(
      'is-popping'
    );

    /*
     * Force a reflow so the animation can be replayed when
     * the same item is favorited again.
     */
    void button.offsetWidth;

    button.classList.add(
      'is-popping'
    );

    button.addEventListener(
      'animationend',
      () => {
        button.classList.remove(
          'is-popping'
        );
      },
      {
        once: true,
      }
    );
  };


  document
    .querySelectorAll(
      '[data-favorite]'
    )
    .forEach((button) => {
      const id =
        button.dataset.favoriteId ||
        button.dataset.favoriteName;

      if (!id) {
        return;
      }

      syncFavorite(
        button,
        favorites.has(id)
      );


      button.addEventListener(
        'click',
        (event) => {
          event.preventDefault();
          event.stopPropagation();

          const willFavorite =
            !favorites.has(id);

          if (willFavorite) {
            favorites.add(id);

            animateFavorite(
              button
            );
          } else {
            favorites.delete(id);
          }

          syncFavorite(
            button,
            willFavorite
          );

          persistFavorites();
        }
      );
    });


  /* ==========================================================
     SEARCH AUTOCOMPLETE
     ========================================================== */

  const searchRoot =
    document.querySelector(
      '[data-search-root]'
    );

  const searchInput =
    searchRoot?.querySelector(
      '[data-search-input]'
    );

  const searchPanel =
    searchRoot?.querySelector(
      '[data-search-panel]'
    );

  const searchEmpty =
    searchRoot?.querySelector(
      '[data-search-empty]'
    );

  const locationInput =
    searchRoot?.querySelector(
      '#home-location-input'
    );

  const suggestions = [
    ...(
      searchRoot?.querySelectorAll(
        '[data-search-suggestion]'
      ) || []
    ),
  ];


  let activeIndex = -1;

  let searchCloseTimer = 0;

  let searchOpenFrame = 0;


  const visibleSuggestions = () =>
    suggestions.filter(
      (item) => !item.hidden
    );


  const clearActiveSuggestion =
    () => {
      activeIndex = -1;

      suggestions.forEach(
        (item) => {
          item.classList.remove(
            'is-active'
          );

          item.setAttribute(
            'aria-selected',
            'false'
          );
        }
      );

      searchInput?.removeAttribute(
        'aria-activedescendant'
      );
    };


  const ensureSuggestionId = (
    item,
    index
  ) => {
    if (!item.id) {
      item.id =
        `home-search-option-${index}`;
    }

    return item.id;
  };


  suggestions.forEach(
    (item, index) => {
      ensureSuggestionId(
        item,
        index
      );

      item.setAttribute(
        'aria-selected',
        'false'
      );
    }
  );


  const setActiveSuggestion = (
    index
  ) => {
    const visible =
      visibleSuggestions();

    if (!visible.length) {
      clearActiveSuggestion();

      return;
    }

    activeIndex =
      (
        index +
        visible.length
      ) %
      visible.length;

    suggestions.forEach(
      (item) => {
        const active =
          item ===
          visible[activeIndex];

        item.classList.toggle(
          'is-active',
          active
        );

        item.setAttribute(
          'aria-selected',
          String(active)
        );
      }
    );

    const activeItem =
      visible[activeIndex];

    if (activeItem) {
      searchInput?.setAttribute(
        'aria-activedescendant',
        activeItem.id
      );

      activeItem.scrollIntoView({
        block: 'nearest',
      });
    }
  };


  const openSuggestions = () => {
    if (
      !searchPanel ||
      !searchInput
    ) {
      return;
    }

    window.clearTimeout(
      searchCloseTimer
    );

    window.cancelAnimationFrame(
      searchOpenFrame
    );

    searchPanel.hidden = false;

    searchInput.setAttribute(
      'aria-expanded',
      'true'
    );

    searchOpenFrame =
      window.requestAnimationFrame(
        () => {
          searchPanel.classList.add(
            'is-open'
          );

          searchOpenFrame = 0;
        }
      );
  };


  const closeSuggestions = () => {
    if (
      !searchPanel ||
      !searchInput
    ) {
      return;
    }

    window.clearTimeout(
      searchCloseTimer
    );

    window.cancelAnimationFrame(
      searchOpenFrame
    );

    searchOpenFrame = 0;

    searchPanel.classList.remove(
      'is-open'
    );

    searchInput.setAttribute(
      'aria-expanded',
      'false'
    );

    clearActiveSuggestion();

    if (reducedMotion) {
      searchPanel.hidden = true;

      return;
    }

    searchCloseTimer =
      window.setTimeout(
        () => {
          searchPanel.hidden = true;
        },
        220
      );
  };


  const syncSearchVisualLabel =
    () => {
      if (!searchInput) {
        return;
      }

      const visualLabel =
        searchInput
          .closest('label')
          ?.querySelector('small');

      if (!visualLabel) {
        return;
      }

      visualLabel.textContent =
        searchInput.value ||
        'Serviço, profissional ou estabelecimento';
    };


  const filterSuggestions = () => {
    if (
      !searchInput ||
      !searchEmpty
    ) {
      return;
    }

    const query = normalize(
      searchInput.value
    );

    suggestions.forEach(
      (item) => {
        const searchableText =
          normalize(
            item.textContent
          );

        item.hidden =
          Boolean(query) &&
          !searchableText.includes(
            query
          );
      }
    );

    searchEmpty.hidden =
      visibleSuggestions()
        .length > 0;

    clearActiveSuggestion();
  };


  searchInput?.addEventListener(
    'focus',
    () => {
      filterSuggestions();

      openSuggestions();
    }
  );


  searchInput?.addEventListener(
    'input',
    () => {
      filterSuggestions();

      syncSearchVisualLabel();

      openSuggestions();
    }
  );


  searchInput?.addEventListener(
    'keydown',
    (event) => {
      if (
        event.key ===
        'ArrowDown'
      ) {
        event.preventDefault();

        openSuggestions();

        setActiveSuggestion(
          activeIndex + 1
        );

        return;
      }


      if (
        event.key ===
        'ArrowUp'
      ) {
        event.preventDefault();

        const visible =
          visibleSuggestions();

        setActiveSuggestion(
          activeIndex < 0
            ? visible.length - 1
            : activeIndex - 1
        );

        return;
      }


      if (
        event.key ===
        'Escape'
      ) {
        event.preventDefault();

        closeSuggestions();

        return;
      }


      if (
        event.key ===
          'Enter' &&
        activeIndex >= 0
      ) {
        const activeItem =
          visibleSuggestions()[
            activeIndex
          ];

        if (!activeItem) {
          return;
        }

        event.preventDefault();

        activeItem.click();
      }
    }
  );


  suggestions.forEach(
    (item) => {
      item.addEventListener(
        'click',
        () => {
          if (!searchInput) {
            return;
          }

          searchInput.value =
            item.dataset.searchValue ||
            item.textContent.trim();

          syncSearchVisualLabel();

          closeSuggestions();

          locationInput?.focus();
        }
      );
    }
  );


  locationInput?.addEventListener(
    'input',
    () => {
      const visualLabel =
        locationInput
          .closest('label')
          ?.querySelector('small');

      if (!visualLabel) {
        return;
      }

      visualLabel.textContent =
        locationInput.value ||
        'Cidade ou bairro';
    }
  );


  document.addEventListener(
    'pointerdown',
    (event) => {
      if (!searchRoot) {
        return;
      }

      const target =
        event.target;

      if (
        target instanceof Node &&
        !searchRoot.contains(target)
      ) {
        closeSuggestions();
      }
    }
  );


  /*
   * If the user changes focus with the keyboard instead of
   * clicking elsewhere, close the panel once focus leaves the
   * complete search component.
   */
  searchRoot?.addEventListener(
    'focusout',
    () => {
      window.setTimeout(
        () => {
          if (
            searchRoot.contains(
              document.activeElement
            )
          ) {
            return;
          }

          closeSuggestions();
        },
        0
      );
    }
  );


  /* ==========================================================
     HORIZONTAL RAILS
     ========================================================== */

  const railControls = [
    ...document.querySelectorAll(
      '[data-rail-control]'
    ),
  ];

  const railProgresses = [
    ...document.querySelectorAll(
      '[data-rail-progress]'
    ),
  ];


  const getRailProgress = (
    rail
  ) =>
    railProgresses.find(
      (item) =>
        item.dataset.railFor ===
        rail.id
    );


  const getRailControls = (
    rail
  ) =>
    railControls.filter(
      (control) =>
        control.dataset.railTarget ===
        rail.id
    );


  const syncRailControls = (
    rail
  ) => {
    const maxScroll =
      Math.max(
        rail.scrollWidth -
          rail.clientWidth,
        0
      );


    getRailControls(
      rail
    ).forEach(
      (control) => {
        const direction =
          Number(
            control.dataset
              .railDirection ||
            1
          );

        if (direction < 0) {
          control.disabled =
            rail.scrollLeft <= 2;
        } else {
          control.disabled =
            maxScroll === 0 ||
            rail.scrollLeft >=
              maxScroll - 2;
        }
      }
    );


    const progress =
      getRailProgress(
        rail
      );

    if (!progress) {
      return;
    }


    const percentage =
      maxScroll > 0
        ? Math.min(
            100,
            Math.max(
              0,
              (
                rail.scrollLeft /
                maxScroll
              ) *
                100
            )
          )
        : 100;


    progress.style.setProperty(
      '--rail-progress',
      `${percentage}%`
    );

    progress.setAttribute(
      'aria-valuenow',
      String(
        Math.round(
          percentage
        )
      )
    );
  };


  const scrollRail = (
    rail,
    direction
  ) => {
    const amount =
      Math.min(
        430,
        rail.clientWidth *
          0.82
      );

    rail.scrollBy({
      left:
        direction *
        amount,

      behavior:
        reducedMotion
          ? 'auto'
          : 'smooth',
    });
  };


  railControls.forEach(
    (control) => {
      const target =
        control.dataset.railTarget;

      if (!target) {
        return;
      }

      const rail =
        document.getElementById(
          target
        );

      if (!rail) {
        return;
      }


      control.addEventListener(
        'click',
        () => {
          const direction =
            Number(
              control.dataset
                .railDirection ||
              1
            );

          scrollRail(
            rail,
            direction
          );
        }
      );
    }
  );


  document
    .querySelectorAll(
      '[data-horizontal-rail]'
    )
    .forEach((rail) => {
      let railFrame = 0;


      const sync = () => {
        if (railFrame) {
          return;
        }

        railFrame =
          window.requestAnimationFrame(
            () => {
              syncRailControls(
                rail
              );

              railFrame = 0;
            }
          );
      };


      rail.addEventListener(
        'scroll',
        sync,
        {
          passive: true,
        }
      );


      rail.addEventListener(
        'keydown',
        (event) => {
          if (
            ![
              'ArrowLeft',
              'ArrowRight',
            ].includes(
              event.key
            )
          ) {
            return;
          }

          event.preventDefault();

          scrollRail(
            rail,
            event.key ===
              'ArrowRight'
              ? 1
              : -1
          );
        }
      );


      if (
        'ResizeObserver'
        in window
      ) {
        const observer =
          new ResizeObserver(
            sync
          );

        observer.observe(
          rail
        );
      }


      sync();
    });


  /* ==========================================================
     PROFESSIONAL AVATAR FALLBACK
     ========================================================== */

  document
    .querySelectorAll(
      '[data-avatar-image]'
    )
    .forEach((image) => {
      const container =
        image.closest(
          '.home-v4-professional-card__image'
        );


      const showFallback =
        () => {
          container?.classList.add(
            'has-fallback'
          );
        };


      image.addEventListener(
        'error',
        showFallback,
        {
          once: true,
        }
      );


      if (
        image.complete &&
        image.naturalWidth === 0
      ) {
        showFallback();
      }
    });


  /* ==========================================================
     HOME NAVIGATION SCROLL SPY
     ========================================================== */

  const navLinks = [
    ...document.querySelectorAll(
      '.home-page .main-nav a[href^="#"]'
    ),
  ];


  const sectionMap =
    navLinks
      .map((link) => {
        const href =
          link.getAttribute(
            'href'
          );

        if (
          !href ||
          href === '#'
        ) {
          return null;
        }

        return {
          link,
          section:
            document.querySelector(
              href
            ),
        };
      })
      .filter(
        (item) =>
          item?.section
      );


  if (
    'IntersectionObserver'
      in window &&
    sectionMap.length
  ) {
    const sectionObserver =
      new IntersectionObserver(
        (entries) => {
          entries.forEach(
            (entry) => {
              if (
                !entry
                  .isIntersecting
              ) {
                return;
              }

              sectionMap.forEach(
                ({
                  link,
                  section,
                }) => {
                  const active =
                    section ===
                    entry.target;

                  link.classList.toggle(
                    'is-active',
                    active
                  );

                  if (active) {
                    link.setAttribute(
                      'aria-current',
                      'page'
                    );
                  } else {
                    link.removeAttribute(
                      'aria-current'
                    );
                  }
                }
              );
            }
          );
        },
        {
          rootMargin:
            '-28% 0px -60% 0px',
        }
      );


    sectionMap.forEach(
      ({ section }) => {
        sectionObserver.observe(
          section
        );
      }
    );
  }


  /* ==========================================================
     HERO POINTER PARALLAX
     ========================================================== */

  if (
    !reducedMotion &&
    !prefersCoarsePointer.matches
  ) {
    const hero =
      document.querySelector(
        '[data-hero]'
      );

    const portrait =
      hero?.querySelector(
        '[data-parallax-media]'
      );


    if (
      hero &&
      portrait
    ) {
      let frame = 0;

      let targetX = 0;

      let targetY = 0;


      const paint = () => {
        portrait.style.setProperty(
          '--hero-shift-x',
          `${targetX.toFixed(
            2
          )}px`
        );

        portrait.style.setProperty(
          '--hero-shift-y',
          `${targetY.toFixed(
            2
          )}px`
        );

        frame = 0;
      };


      const requestPaint = () => {
        if (frame) {
          return;
        }

        frame =
          window.requestAnimationFrame(
            paint
          );
      };


      hero.addEventListener(
        'pointermove',
        (event) => {
          const rect =
            hero.getBoundingClientRect();


          const x =
            (
              (
                event.clientX -
                rect.left
              ) /
                Math.max(
                  rect.width,
                  1
                )
            ) -
            0.5;


          const y =
            (
              (
                event.clientY -
                rect.top
              ) /
                Math.max(
                  rect.height,
                  1
                )
            ) -
            0.5;


          targetX =
            x * -7;

          targetY =
            y * -5;


          requestPaint();
        }
      );


      hero.addEventListener(
        'pointerleave',
        () => {
          targetX = 0;

          targetY = 0;

          requestPaint();
        }
      );
    }
  }


  /* ==========================================================
     APP MOCKUP SCROLL PARALLAX
     ========================================================== */

  const appVisual =
    document.querySelector(
      '[data-app-parallax]'
    );

  const appSection =
    appVisual?.closest(
      '.home-v4-app'
    );


  if (
    !reducedMotion &&
    appVisual &&
    appSection
  ) {
    let appFrame = 0;


    const paintAppParallax =
      () => {
        const rect =
          appSection
            .getBoundingClientRect();

        const viewport =
          window.innerHeight ||
          1;


        const centerDelta =
          (
            rect.top +
            rect.height / 2 -
            viewport / 2
          ) /
          viewport;


        const progress =
          Math.max(
            -1,
            Math.min(
              1,
              centerDelta
            )
          );


        appVisual.style.setProperty(
          '--phone-shift-front',
          `${
            (
              progress *
              -10
            ).toFixed(2)
          }px`
        );


        appVisual.style.setProperty(
          '--phone-shift-back',
          `${
            (
              progress *
              7
            ).toFixed(2)
          }px`
        );


        appFrame = 0;
      };


    const requestAppParallax =
      () => {
        if (appFrame) {
          return;
        }

        appFrame =
          window.requestAnimationFrame(
            paintAppParallax
          );
      };


    paintAppParallax();


    window.addEventListener(
      'scroll',
      requestAppParallax,
      {
        passive: true,
      }
    );


    window.addEventListener(
      'resize',
      requestAppParallax,
      {
        passive: true,
      }
    );
  }


  /* ==========================================================
     DISABLED PLACEHOLDER LINKS
     ========================================================== */

  document
    .querySelectorAll(
      '[aria-disabled="true"]'
    )
    .forEach((element) => {
      if (
        element.tagName !== 'A'
      ) {
        return;
      }

      element.addEventListener(
        'click',
        (event) => {
          event.preventDefault();
        }
      );

      element.setAttribute(
        'tabindex',
        '-1'
      );
    });
})();