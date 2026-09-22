document.addEventListener('DOMContentLoaded', () => {
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
      window.requestAnimationFrame(() => searchDialog.querySelector('[data-header-search-input]')?.focus());
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
