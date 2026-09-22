(() => {
  const root = document.querySelector('[data-marketplace-root]');
  if (!root) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const filterDialog = root.querySelector('[data-filter-dialog]');
  const openFilters = root.querySelector('[data-open-filters]');
  const closeFilters = root.querySelector('[data-close-filters]');
  const skeleton = root.querySelector('[data-catalog-skeleton]');
  const resultsContent = root.querySelector('[data-results-content]');
  const resultCount = root.querySelector('[data-results-count]');
  const emptyState = root.querySelector('[data-client-empty]');
  const catalogGrid = root.querySelector('[data-catalog-grid]');
  const featuredWrap = root.querySelector('[data-featured-wrap]');
  const favoriteStorageKey = 'iddun:favorites:v1';

  const readFavorites = () => {
    try {
      const stored = JSON.parse(window.localStorage.getItem(favoriteStorageKey) || '[]');
      return new Set(Array.isArray(stored) ? stored : []);
    } catch (_) {
      return new Set();
    }
  };

  const favorites = readFavorites();

  const persistFavorites = () => {
    try {
      window.localStorage.setItem(favoriteStorageKey, JSON.stringify([...favorites]));
    } catch (_) {
      // A experiência continua funcional quando o navegador bloqueia storage.
    }
  };

  const syncFavoriteButton = (button, active) => {
    const title = button.dataset.favoriteTitle || 'experiência';
    button.dataset.active = String(active);
    button.setAttribute('aria-pressed', String(active));
    button.setAttribute('aria-label', `${active ? 'Remover dos favoritos' : 'Favoritar'} ${title}`);
  };

  root.querySelectorAll('[data-favorite]').forEach((button) => {
    const id = button.dataset.favoriteId;
    syncFavoriteButton(button, favorites.has(id));

    button.addEventListener('click', () => {
      const nextActive = !favorites.has(id);
      if (nextActive) favorites.add(id);
      else favorites.delete(id);
      persistFavorites();

      root.querySelectorAll(`[data-favorite-id="${CSS.escape(id)}"]`).forEach((matchingButton) => {
        syncFavoriteButton(matchingButton, nextActive);
        if (!reduceMotion) {
          matchingButton.classList.remove('is-popping');
          window.requestAnimationFrame(() => matchingButton.classList.add('is-popping'));
          window.setTimeout(() => matchingButton.classList.remove('is-popping'), 320);
        }
      });
    });
  });

  const setLoading = (loading) => {
    if (!skeleton || !resultsContent) return;
    skeleton.hidden = !loading;
    resultsContent.hidden = loading;
    root.setAttribute('aria-busy', String(loading));
  };

  const applyClientFilter = (category, targetUrl) => {
    const cards = [...root.querySelectorAll('[data-experience-card]')];
    setLoading(true);

    window.setTimeout(() => {
      let visibleCount = 0;
      let visibleRegularCount = 0;

      cards.forEach((card) => {
        const matches = !category || card.dataset.category === category;
        card.hidden = !matches;
        if (matches) {
          visibleCount += 1;
          if (card.classList.contains('catalog-card')) visibleRegularCount += 1;
          if (!reduceMotion) {
            card.animate(
              [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }],
              { duration: 220, easing: 'ease-out' },
            );
          }
        }
      });

      const featuredCard = featuredWrap?.querySelector('[data-experience-card]');
      if (featuredWrap) featuredWrap.hidden = !featuredCard || featuredCard.hidden;
      if (catalogGrid) catalogGrid.hidden = visibleRegularCount === 0;
      if (emptyState) emptyState.hidden = visibleCount !== 0;

      root.querySelectorAll('[data-category-filter]').forEach((chip) => {
        const active = chip.dataset.categoryFilter === category;
        chip.classList.toggle('is-active', active);
        chip.setAttribute('aria-pressed', String(active));
      });

      if (resultCount) {
        resultCount.textContent = `${visibleCount} ${visibleCount === 1 ? 'experiência encontrada' : 'experiências encontradas'}`;
      }

      if (targetUrl) window.history.pushState({ category }, '', targetUrl);
      setLoading(false);
    }, reduceMotion ? 0 : 240);
  };

  if (root.dataset.clientFilterReady === 'true') {
    root.querySelectorAll('[data-category-filter]').forEach((chip) => {
      chip.addEventListener('click', (event) => {
        event.preventDefault();
        applyClientFilter(chip.dataset.categoryFilter || '', chip.href);
      });
    });

    window.addEventListener('popstate', () => window.location.reload());
  }

  root.querySelectorAll('form[role="search"], .inline-filters').forEach((form) => {
    form.addEventListener('submit', () => setLoading(true));
  });

  const closeFilterDialog = () => {
    if (!filterDialog?.open) return;
    if (typeof filterDialog.close === 'function') filterDialog.close();
    else filterDialog.removeAttribute('open');
  };

  if (filterDialog && openFilters) {
    openFilters.addEventListener('click', () => {
      if (typeof filterDialog.showModal === 'function') filterDialog.showModal();
      else filterDialog.setAttribute('open', '');
    });
    closeFilters?.addEventListener('click', closeFilterDialog);
    filterDialog.addEventListener('click', (event) => {
      if (event.target === filterDialog) closeFilterDialog();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeFilterDialog();
    });
  }
})();
