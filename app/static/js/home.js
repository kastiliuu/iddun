(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FAVORITES_KEY = 'iddun:favorites:v2';

  const normalize = (value) => value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .trim();

  /* Favorite professionals and studios, persisting the state locally. */
  let favorites = new Set();
  try {
    favorites = new Set(JSON.parse(window.localStorage.getItem(FAVORITES_KEY) || '[]'));
  } catch (_) {
    favorites = new Set();
  }

  const syncFavorite = (button, active) => {
    const name = button.dataset.favoriteName || 'item';
    button.dataset.active = String(active);
    button.setAttribute('aria-pressed', String(active));
    button.setAttribute('aria-label', `${active ? 'Remover dos favoritos' : 'Favoritar'}: ${name}`);
  };

  document.querySelectorAll('[data-favorite]').forEach((button) => {
    const id = button.dataset.favoriteId || button.dataset.favoriteName;
    syncFavorite(button, favorites.has(id));

    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const active = !favorites.has(id);
      if (active) favorites.add(id);
      else favorites.delete(id);
      syncFavorite(button, active);

      try {
        window.localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
      } catch (_) {
        /* Storage can be blocked without blocking the interaction. */
      }
    });
  });

  /* Search autocomplete with keyboard support. */
  const searchRoot = document.querySelector('[data-search-root]');
  const searchForm = searchRoot?.querySelector('[data-home-search]');
  const searchInput = searchRoot?.querySelector('[data-search-input]');
  const searchPanel = searchRoot?.querySelector('[data-search-panel]');
  const searchEmpty = searchRoot?.querySelector('[data-search-empty]');
  const suggestions = [...(searchRoot?.querySelectorAll('[data-search-suggestion]') || [])];
  let activeIndex = -1;

  const visibleSuggestions = () => suggestions.filter((item) => !item.hidden);

  const clearActiveSuggestion = () => {
    activeIndex = -1;
    suggestions.forEach((item) => {
      item.classList.remove('is-active');
      item.setAttribute('aria-selected', 'false');
    });
  };

  const setActiveSuggestion = (index) => {
    const visible = visibleSuggestions();
    if (!visible.length) return clearActiveSuggestion();
    activeIndex = (index + visible.length) % visible.length;
    suggestions.forEach((item) => {
      const active = item === visible[activeIndex];
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-selected', String(active));
    });
    visible[activeIndex]?.scrollIntoView({ block: 'nearest' });
  };

  const openSuggestions = () => {
    if (!searchPanel || !searchInput) return;
    searchPanel.hidden = false;
    searchInput.setAttribute('aria-expanded', 'true');
  };

  const closeSuggestions = () => {
    if (!searchPanel || !searchInput) return;
    searchPanel.hidden = true;
    searchInput.setAttribute('aria-expanded', 'false');
    clearActiveSuggestion();
  };

  const filterSuggestions = () => {
    if (!searchInput || !searchEmpty) return;
    const query = normalize(searchInput.value);
    suggestions.forEach((item) => {
      item.hidden = Boolean(query) && !normalize(item.textContent).includes(query);
    });
    searchEmpty.hidden = visibleSuggestions().length > 0;
    clearActiveSuggestion();
  };

  searchInput?.addEventListener('focus', () => {
    filterSuggestions();
    openSuggestions();
  });
  searchInput?.addEventListener('input', () => {
    filterSuggestions();
    openSuggestions();
  });
  searchInput?.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      openSuggestions();
      setActiveSuggestion(activeIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSuggestion(activeIndex < 0 ? visibleSuggestions().length - 1 : activeIndex - 1);
    } else if (event.key === 'Escape') {
      closeSuggestions();
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      visibleSuggestions()[activeIndex]?.click();
    }
  });

  suggestions.forEach((item) => {
    item.addEventListener('click', () => {
      if (!searchInput) return;
      searchInput.value = item.dataset.searchValue || item.textContent.trim();
      const visualLabel = searchInput.closest('label')?.querySelector('small');
      if (visualLabel) visualLabel.textContent = searchInput.value;
      closeSuggestions();
      searchRoot?.querySelector('#home-location-input')?.focus();
    });
  });

  searchInput?.addEventListener('input', () => {
    const visualLabel = searchInput.closest('label')?.querySelector('small');
    if (visualLabel) visualLabel.textContent = searchInput.value || 'Ex: corte, manicure, massagem...';
  });

  const locationInput = searchRoot?.querySelector('#home-location-input');
  locationInput?.addEventListener('input', () => {
    const visualLabel = locationInput.closest('label')?.querySelector('small');
    if (visualLabel) visualLabel.textContent = locationInput.value || 'Cidade ou bairro';
  });

  document.addEventListener('pointerdown', (event) => {
    if (searchRoot && !searchRoot.contains(event.target)) closeSuggestions();
  });

  /* Date field starts today and mirrors a human-readable value. */
  const dateInput = document.querySelector('[data-date-input]');
  const dateLabel = document.querySelector('[data-date-label]');
  if (dateInput) {
    const now = new Date();
    const localToday = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
    dateInput.min = localToday;
    dateInput.addEventListener('change', () => {
      if (!dateLabel) return;
      if (!dateInput.value) {
        dateLabel.textContent = 'Selecione uma data';
        return;
      }
      dateLabel.textContent = new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',
      }).format(new Date(`${dateInput.value}T00:00:00Z`));
    });
  }

  /* Horizontal rails used by professionals and studios. */
  const railControls = [...document.querySelectorAll('[data-rail-control]')];

  const syncRailControls = (rail) => {
    const maxScroll = Math.max(rail.scrollWidth - rail.clientWidth, 0);
    railControls
      .filter((control) => control.dataset.railTarget === rail.id)
      .forEach((control) => {
        const direction = Number(control.dataset.railDirection || 1);
        control.disabled = direction < 0
          ? rail.scrollLeft <= 2
          : rail.scrollLeft >= maxScroll - 2 || maxScroll === 0;
      });
  };

  railControls.forEach((control) => {
    const rail = document.getElementById(control.dataset.railTarget);
    if (!rail) return;
    control.addEventListener('click', () => {
      rail.scrollBy({
        left: Number(control.dataset.railDirection || 1) * Math.min(430, rail.clientWidth * .82),
        behavior: reducedMotion ? 'auto' : 'smooth',
      });
    });
  });

  document.querySelectorAll('[data-horizontal-rail]').forEach((rail) => {
    const sync = () => syncRailControls(rail);
    rail.addEventListener('scroll', sync, { passive: true });
    rail.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      rail.scrollBy({
        left: (event.key === 'ArrowRight' ? 1 : -1) * Math.min(430, rail.clientWidth * .82),
        behavior: reducedMotion ? 'auto' : 'smooth',
      });
    });
    if ('ResizeObserver' in window) new ResizeObserver(sync).observe(rail);
    sync();
  });

  /* Avatar fallback prevents broken image text from entering the layout. */
  document.querySelectorAll('[data-avatar-image]').forEach((image) => {
    const container = image.closest('.home-v4-professional-card__image');
    const fallback = () => container?.classList.add('has-fallback');
    image.addEventListener('error', fallback, { once: true });
    if (image.complete && image.naturalWidth === 0) fallback();
  });

  /* Active navigation follows the current section. */
  const navLinks = [...document.querySelectorAll('.home-page .main-nav a[href^="#"]')];
  const sectionMap = navLinks
    .map((link) => ({ link, section: document.querySelector(link.getAttribute('href')) }))
    .filter((item) => item.section);

  if ('IntersectionObserver' in window) {
    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        sectionMap.forEach(({ link, section }) => {
          const active = section === entry.target;
          link.classList.toggle('is-active', active);
          if (active) link.setAttribute('aria-current', 'page');
          else link.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-28% 0px -60% 0px' });
    sectionMap.forEach(({ section }) => sectionObserver.observe(section));
  }

  /* Restrained pointer parallax for the hero portrait. */
  if (reducedMotion || window.matchMedia('(pointer: coarse)').matches) return;
  const hero = document.querySelector('[data-hero]');
  const portrait = hero?.querySelector('[data-parallax-media]');
  if (!hero || !portrait) return;

  let frame = 0;
  let targetX = 0;
  let targetY = 0;
  const paint = () => {
    portrait.style.setProperty('--hero-shift-x', `${targetX.toFixed(2)}px`);
    portrait.style.setProperty('--hero-shift-y', `${targetY.toFixed(2)}px`);
    frame = 0;
  };

  hero.addEventListener('pointermove', (event) => {
    const rect = hero.getBoundingClientRect();
    targetX = (((event.clientX - rect.left) / Math.max(rect.width, 1)) - .5) * -7;
    targetY = (((event.clientY - rect.top) / Math.max(rect.height, 1)) - .5) * -5;
    if (!frame) frame = requestAnimationFrame(paint);
  });
  hero.addEventListener('pointerleave', () => {
    targetX = 0;
    targetY = 0;
    if (!frame) frame = requestAnimationFrame(paint);
  });
})();
