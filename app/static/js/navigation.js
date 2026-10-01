document.addEventListener('DOMContentLoaded', () => {
  const csrfRefreshInterval = 45 * 60 * 1000;
  let csrfRefreshPromise = null;
  let lastCsrfRefreshAt = Date.now();

  const csrfFields = () => document.querySelectorAll('input[name="csrf_token"]');

  const refreshCsrfToken = () => {
    if (!csrfFields().length) return Promise.resolve(false);
    if (csrfRefreshPromise) return csrfRefreshPromise;

    csrfRefreshPromise = fetch('/csrf-token', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
      },
    })
      .then((response) => {
        if (!response.ok) throw new Error('Não foi possível renovar o token CSRF.');
        return response.json();
      })
      .then((payload) => {
        if (!payload || typeof payload.csrfToken !== 'string' || !payload.csrfToken) {
          throw new Error('A resposta de renovação do CSRF é inválida.');
        }

        csrfFields().forEach((field) => {
          field.value = payload.csrfToken;
        });

        lastCsrfRefreshAt = Date.now();
        return true;
      })
      .catch(() => false)
      .finally(() => {
        csrfRefreshPromise = null;
      });

    return csrfRefreshPromise;
  };

  if (csrfFields().length) {
    window.setInterval(() => {
      if (document.visibilityState === 'visible') refreshCsrfToken();
    }, csrfRefreshInterval);

    document.addEventListener('visibilitychange', () => {
      const refreshIsDue = Date.now() - lastCsrfRefreshAt >= csrfRefreshInterval;

      if (document.visibilityState === 'visible' && refreshIsDue) {
        refreshCsrfToken();
      }
    });

    window.addEventListener('pageshow', (event) => {
      if (event.persisted) refreshCsrfToken();
    });

    window.addEventListener('online', () => {
      const refreshIsDue = Date.now() - lastCsrfRefreshAt >= csrfRefreshInterval;
      if (refreshIsDue) refreshCsrfToken();
    });
  }

  const mobileMenu = document.querySelector('[data-mobile-menu]');
  const siteHeader = document.querySelector('[data-site-header]');
  const searchDialog = document.querySelector('[data-header-search-dialog]');
  const searchOpen = document.querySelector('[data-header-search-open]');
  const searchClose = document.querySelector('[data-header-search-close]');

  if (!siteHeader) return;

  const syncHeaderSurface = () => {
    siteHeader.classList.toggle('is-scrolled', window.scrollY > 20);
  };

  syncHeaderSurface();
  window.addEventListener('scroll', syncHeaderSurface, { passive: true });

  const closeSearch = () => {
    if (!searchDialog || !searchDialog.open) return;
    searchDialog.close();
    searchOpen?.setAttribute('aria-expanded', 'false');
    document.documentElement.classList.remove('has-dialog-open');
    searchOpen?.focus();
  };

  if (searchDialog && searchOpen) {
    searchOpen.addEventListener('click', () => {
      if (typeof searchDialog.showModal === 'function') searchDialog.showModal();
      else searchDialog.setAttribute('open', '');

      searchOpen.setAttribute('aria-expanded', 'true');
      document.documentElement.classList.add('has-dialog-open');

      window.requestAnimationFrame(() => {
        searchDialog.querySelector('[data-header-search-input]')?.focus();
      });
    });

    searchClose?.addEventListener('click', closeSearch);

    searchDialog.addEventListener('click', (event) => {
      if (event.target === searchDialog) closeSearch();
    });

    searchDialog.addEventListener('close', () => {
      searchOpen.setAttribute('aria-expanded', 'false');
      document.documentElement.classList.remove('has-dialog-open');
    });
  }

  if (!mobileMenu) return;

  const closeMobileMenu = () => {
    siteHeader.classList.remove('is-menu-open');
    mobileMenu.setAttribute('aria-expanded', 'false');
    mobileMenu.setAttribute('aria-label', 'Abrir menu');
  };

  mobileMenu.addEventListener('click', () => {
    const open = siteHeader.classList.toggle('is-menu-open');

    mobileMenu.setAttribute('aria-expanded', String(open));
    mobileMenu.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  });

  siteHeader.querySelectorAll('.main-nav a').forEach((link) => {
    link.addEventListener('click', closeMobileMenu);
  });

  document.addEventListener('click', (event) => {
    if (!siteHeader.classList.contains('is-menu-open')) return;
    if (siteHeader.contains(event.target)) return;

    closeMobileMenu();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeMobileMenu();
      closeSearch();
    }
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 1080) closeMobileMenu();
  });
});