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


  const hasActiveFiltersInUrl = (
    targetUrl
  ) => {
    const url = new URL(
      targetUrl ||
        window.location.href,
      window.location.href
    );

    const sort =
      url.searchParams.get(
        'ordem'
      );

    return Boolean(
      url.searchParams
        .get('q')
        ?.trim() ||
      url.searchParams
        .get('categoria')
        ?.trim() ||
      url.searchParams
        .get('bairro')
        ?.trim() ||
      (
        sort &&
        sort !== 'recommended'
      )
    );
  };


  const syncFilterIndicator = (
    targetUrl
  ) => {
    if (!openFilters) {
      return;
    }

    const active =
      hasActiveFiltersInUrl(
        targetUrl
      );

    let dot =
      openFilters.querySelector(
        '.marketplace-filter-button__dot'
      );

    if (!dot) {
      dot =
        document.createElement(
          'span'
        );

      dot.className =
        'marketplace-filter-button__dot';

      dot.setAttribute(
        'aria-hidden',
        'true'
      );

      openFilters.append(dot);
    }

    dot.hidden = !active;

    openFilters.dataset
      .hasActiveFilters =
        String(active);

    openFilters.setAttribute(
      'aria-label',
      active
        ? 'Abrir filtros. Existem filtros ativos.'
        : 'Abrir filtros'
    );
  };


  /* ==========================================================
     FAVORITES
     ==========================================================
     Salvar uma experiência agora grava na conta pela API do grafo
     (graph.js, D-SOC-05). Os favoritos que ficavam só neste navegador
     são enviados uma vez para a conta e apagados daqui.
     ========================================================== */


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

  syncFilterIndicator(
    window.location.href
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


          /*
           * (a) Category chips are navigation links, not
           * toggle buttons. aria-current is the correct
           * semantic state for the selected destination.
           */

          chip.removeAttribute(
            'aria-pressed'
          );


          if (active) {
            chip.setAttribute(
              'aria-current',
              'page'
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

    syncFilterIndicator(
      targetUrl ||
        window.location.href
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
    }
  );
})();
