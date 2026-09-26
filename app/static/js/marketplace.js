(() => {
  'use strict';

  /* ==========================================================
     IDDUN — DISCOVERY / MARKETPLACE
     ========================================================== */

  const root = document.querySelector(
    '[data-marketplace-root]'
  );

  if (!root) {
    return;
  }


  /* ==========================================================
     ENVIRONMENT
     ========================================================== */

  const reduceMotion =
    window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches;


  /* ==========================================================
     DOM
     ========================================================== */

  const filterDialog =
    root.querySelector(
      '[data-filter-dialog]'
    );

  const openFilters =
    root.querySelector(
      '[data-open-filters]'
    );

  const closeFilters =
    root.querySelector(
      '[data-close-filters]'
    );

  const skeleton =
    root.querySelector(
      '[data-catalog-skeleton]'
    );

  const resultsContent =
    root.querySelector(
      '[data-results-content]'
    );

  const resultCount =
    root.querySelector(
      '[data-results-count]'
    );

  const emptyState =
    root.querySelector(
      '[data-client-empty]'
    );

  const catalogGrid =
    root.querySelector(
      '[data-catalog-grid]'
    );

  const featuredWrap =
    root.querySelector(
      '[data-featured-wrap]'
    );


  /* ==========================================================
     HELPERS
     ========================================================== */

  const normalizeKey = (
    value
  ) =>
    String(
      value ?? ''
    )
      .trim()
      .toLocaleLowerCase(
        'pt-BR'
      );


  const parseStoredArray = (
    value
  ) => {
    try {
      const parsed =
        JSON.parse(
          value || '[]'
        );

      return Array.isArray(
        parsed
      )
        ? parsed
        : [];
    } catch (_) {
      return [];
    }
  };


  /* ==========================================================
     FAVORITES
     ========================================================== */

  /*
   * The Home already uses v2.
   *
   * v1 is still read temporarily so favorites created by the
   * previous marketplace implementation are not lost.
   *
   * When the real favorites API is implemented, this local
   * persistence must be replaced by the authenticated backend.
   */

  const FAVORITES_KEY =
    'iddun:favorites:v2';

  const LEGACY_FAVORITES_KEY =
    'iddun:favorites:v1';


  const readFavorites = () => {
    const current =
      parseStoredArray(
        window.localStorage.getItem(
          FAVORITES_KEY
        )
      );

    const legacy =
      parseStoredArray(
        window.localStorage.getItem(
          LEGACY_FAVORITES_KEY
        )
      );

    return new Set([
      ...current,
      ...legacy,
    ]);
  };


  const favorites =
    readFavorites();


  const persistFavorites =
    () => {
      try {
        window.localStorage.setItem(
          FAVORITES_KEY,
          JSON.stringify([
            ...favorites,
          ])
        );
      } catch (_) {
        /*
         * localStorage may be unavailable in restricted
         * environments. Favorites must still work during
         * the current page session.
         */
      }
    };


  /*
   * Persist immediately so existing v1 marketplace favorites
   * are transparently carried into v2.
   */

  persistFavorites();


  const syncFavoriteButton = (
    button,
    active
  ) => {
    const title =
      button.dataset
        .favoriteTitle ||
      'experiência';

    button.dataset.active =
      String(active);

    button.setAttribute(
      'aria-pressed',
      String(active)
    );

    button.setAttribute(
      'aria-label',
      active
        ? `Remover ${title} dos favoritos`
        : `Favoritar ${title}`
    );
  };


  const syncFavoriteId = (
    id
  ) => {
    if (!id) {
      return;
    }

    const active =
      favorites.has(id);

    root
      .querySelectorAll(
        '[data-favorite]'
      )
      .forEach(
        (button) => {
          if (
            button.dataset
              .favoriteId !== id
          ) {
            return;
          }

          syncFavoriteButton(
            button,
            active
          );
        }
      );
  };


  const animateFavorite = (
    button
  ) => {
    if (reduceMotion) {
      return;
    }

    button.classList.remove(
      'is-popping'
    );

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


  root
    .querySelectorAll(
      '[data-favorite]'
    )
    .forEach(
      (button) => {
        const id =
          button.dataset
            .favoriteId;

        if (!id) {
          return;
        }


        syncFavoriteButton(
          button,
          favorites.has(id)
        );


        button.addEventListener(
          'click',
          (event) => {
            /*
             * Defensive because favorite buttons live on top
             * of clickable card media.
             */
            event.preventDefault();
            event.stopPropagation();


            const nextActive =
              !favorites.has(id);


            if (nextActive) {
              favorites.add(id);
            } else {
              favorites.delete(id);
            }


            persistFavorites();

            syncFavoriteId(id);


            root
              .querySelectorAll(
                '[data-favorite]'
              )
              .forEach(
                (
                  matchingButton
                ) => {
                  if (
                    matchingButton
                      .dataset
                      .favoriteId ===
                      id &&
                    nextActive
                  ) {
                    animateFavorite(
                      matchingButton
                    );
                  }
                }
              );
          }
        );
      }
    );


  /*
   * Keep another open IDDUN tab synchronized when local
   * favorites change there.
   */

  window.addEventListener(
    'storage',
    (event) => {
      if (
        event.key !==
        FAVORITES_KEY
      ) {
        return;
      }

      const incoming =
        new Set(
          parseStoredArray(
            event.newValue
          )
        );


      favorites.clear();

      incoming.forEach(
        (id) => {
          favorites.add(id);
        }
      );


      root
        .querySelectorAll(
          '[data-favorite]'
        )
        .forEach(
          (button) => {
            const id =
              button.dataset
                .favoriteId;

            if (!id) {
              return;
            }

            syncFavoriteButton(
              button,
              favorites.has(id)
            );
          }
        );
    }
  );


  /* ==========================================================
     LOADING STATE
     ========================================================== */

  const setLoading = (
    loading
  ) => {
    root.setAttribute(
      'aria-busy',
      String(loading)
    );


    if (skeleton) {
      skeleton.hidden =
        !loading;
    }


    if (resultsContent) {
      resultsContent.hidden =
        loading;
    }
  };


  root.setAttribute(
    'aria-busy',
    'false'
  );


  /* ==========================================================
     CLIENT-SIDE CATEGORY FILTER
     ========================================================== */

  const getExperienceCards =
    () => [
      ...root.querySelectorAll(
        '[data-experience-card]'
      ),
    ];


  const syncCategoryChips = (
    category
  ) => {
    const normalizedCategory =
      normalizeKey(category);


    root
      .querySelectorAll(
        '[data-category-filter]'
      )
      .forEach(
        (chip) => {
          const chipCategory =
            normalizeKey(
              chip.dataset
                .categoryFilter
            );


          const active =
            chipCategory ===
            normalizedCategory;


          chip.classList.toggle(
            'is-active',
            active
          );


          chip.setAttribute(
            'aria-pressed',
            String(active)
          );


          if (active) {
            chip.setAttribute(
              'aria-current',
              'true'
            );
          } else {
            chip.removeAttribute(
              'aria-current'
            );
          }
        }
      );
  };


  const animateResultCard = (
    card
  ) => {
    if (
      reduceMotion ||
      typeof card.animate !==
        'function'
    ) {
      return;
    }


    card.animate(
      [
        {
          opacity: 0,
          transform:
            'translateY(8px)',
        },
        {
          opacity: 1,
          transform:
            'translateY(0)',
        },
      ],
      {
        duration: 220,
        easing:
          'cubic-bezier(.22,.61,.36,1)',
      }
    );
  };


  const applyClientFilter = (
    category,
    targetUrl = null
  ) => {
    const normalizedCategory =
      normalizeKey(category);

    const cards =
      getExperienceCards();

    let visibleCount = 0;

    let visibleRegularCount =
      0;


    cards.forEach(
      (card) => {
        const cardCategory =
          normalizeKey(
            card.dataset.category
          );


        const matches =
          !normalizedCategory ||
          cardCategory ===
            normalizedCategory;


        card.hidden =
          !matches;


        if (!matches) {
          return;
        }


        visibleCount += 1;


        if (
          card.classList.contains(
            'catalog-card'
          )
        ) {
          visibleRegularCount += 1;
        }


        animateResultCard(
          card
        );
      }
    );


    /* --------------------------------------------------------
       FEATURED
       -------------------------------------------------------- */

    if (featuredWrap) {
      const featuredCard =
        featuredWrap.querySelector(
          '[data-experience-card]'
        );

      featuredWrap.hidden =
        !featuredCard ||
        featuredCard.hidden;
    }


    /* --------------------------------------------------------
       REGULAR GRID
       -------------------------------------------------------- */

    if (catalogGrid) {
      catalogGrid.hidden =
        visibleRegularCount === 0;
    }


    /* --------------------------------------------------------
       EMPTY STATE
       -------------------------------------------------------- */

    if (emptyState) {
      emptyState.hidden =
        visibleCount !== 0;
    }


    /* --------------------------------------------------------
       CHIPS
       -------------------------------------------------------- */

    syncCategoryChips(
      normalizedCategory
    );


    /* --------------------------------------------------------
       RESULT COUNT
       -------------------------------------------------------- */

    if (resultCount) {
      resultCount.textContent =
        `${visibleCount} ${
          visibleCount === 1
            ? 'experiência encontrada'
            : 'experiências encontradas'
        }`;
    }


    /* --------------------------------------------------------
       URL
       -------------------------------------------------------- */

    if (targetUrl) {
      window.history.pushState(
        {
          category:
            normalizedCategory,
        },
        '',
        targetUrl
      );
    }
  };


  /* ==========================================================
     CLIENT FILTER ACTIVATION
     ========================================================== */

  if (
    root.dataset
      .clientFilterReady ===
    'true'
  ) {
    root
      .querySelectorAll(
        '[data-category-filter]'
      )
      .forEach(
        (chip) => {
          chip.addEventListener(
            'click',
            (event) => {
              event.preventDefault();


              applyClientFilter(
                chip.dataset
                  .categoryFilter ||
                  '',
                chip.href
              );
            }
          );
        }
      );


    /*
     * A browser-history change can also affect query, location
     * or sort parameters. Reloading guarantees that the Flask
     * server remains the source of truth for those filters.
     */

    window.addEventListener(
      'popstate',
      () => {
        window.location.reload();
      }
    );
  }


  /* ==========================================================
     SERVER FILTER SUBMISSIONS
     ========================================================== */

  root
    .querySelectorAll(
      [
        'form[role="search"]',
        '.inline-filters',
        '.filter-sheet__panel',
      ].join(',')
    )
    .forEach(
      (form) => {
        form.addEventListener(
          'submit',
          () => {
            setLoading(true);
          }
        );
      }
    );


  /* ==========================================================
     FILTER DIALOG
     ========================================================== */

  let filterReturnFocus =
    null;


  const syncFilterTrigger = (
    expanded
  ) => {
    if (!openFilters) {
      return;
    }

    openFilters.setAttribute(
      'aria-expanded',
      String(expanded)
    );
  };


  const closeFilterDialog =
    () => {
      if (!filterDialog) {
        return;
      }


      if (
        filterDialog.open &&
        typeof filterDialog.close ===
          'function'
      ) {
        filterDialog.close();

        return;
      }


      if (
        filterDialog.hasAttribute(
          'open'
        )
      ) {
        filterDialog.removeAttribute(
          'open'
        );
      }


      syncFilterTrigger(
        false
      );


      if (
        filterReturnFocus &&
        typeof filterReturnFocus
          .focus ===
          'function'
      ) {
        filterReturnFocus.focus();
      }
    };


  const openFilterDialog =
    () => {
      if (
        !filterDialog ||
        !openFilters
      ) {
        return;
      }


      filterReturnFocus =
        document.activeElement;


      syncFilterTrigger(
        true
      );


      if (
        typeof filterDialog
          .showModal ===
        'function'
      ) {
        if (!filterDialog.open) {
          filterDialog.showModal();
        }
      } else {
        filterDialog.setAttribute(
          'open',
          ''
        );
      }


      window.requestAnimationFrame(
        () => {
          closeFilters?.focus();
        }
      );
    };


  if (
    filterDialog &&
    openFilters
  ) {
    syncFilterTrigger(
      false
    );


    openFilters.addEventListener(
      'click',
      openFilterDialog
    );


    closeFilters?.addEventListener(
      'click',
      closeFilterDialog
    );


    /*
     * Clicking the backdrop of the native <dialog>.
     */

    filterDialog.addEventListener(
      'click',
      (event) => {
        if (
          event.target ===
          filterDialog
        ) {
          closeFilterDialog();
        }
      }
    );


    /*
     * Native dialog emits cancel for Escape.
     * Calling our own close routine keeps aria-expanded and
     * focus restoration synchronized.
     */

    filterDialog.addEventListener(
      'cancel',
      (event) => {
        event.preventDefault();

        closeFilterDialog();
      }
    );


    /*
     * Also runs when the dialog is closed through another
     * native mechanism.
     */

    filterDialog.addEventListener(
      'close',
      () => {
        syncFilterTrigger(
          false
        );


        if (
          filterReturnFocus &&
          typeof filterReturnFocus
            .focus ===
            'function'
        ) {
          filterReturnFocus.focus();
        }


        filterReturnFocus =
          null;
      }
    );
  }


  /* ==========================================================
     CLEANUP AFTER PAGE RESTORE
     ========================================================== */

  window.addEventListener(
    'pageshow',
    () => {
      /*
       * When the page returns from browser back/forward cache,
       * a loading state from the previous navigation must not
       * remain visible.
       */

      setLoading(false);


      root
        .querySelectorAll(
          '[data-favorite]'
        )
        .forEach(
          (button) => {
            const id =
              button.dataset
                .favoriteId;

            if (!id) {
              return;
            }


            syncFavoriteButton(
              button,
              favorites.has(id)
            );
          }
        );
    }
  );
})();