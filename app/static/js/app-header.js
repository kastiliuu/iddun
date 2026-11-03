/*
 * Cabeçalho das telas logadas (PR 1, D-SOC-04): busca com sugestões,
 * menu Eu com os contextos, Favoritos e Notificações. Antes vivia em
 * feed.js; agora atende todas as páginas que usam o cabeçalho único.
 */
(() => {
  const searchRoot = document.querySelector(
    '[data-feed-search]',
  );

  const searchInput = document.querySelector(
    '[data-feed-search-input]',
  );

  const searchResults = document.querySelector(
    '[data-feed-search-results]',
  );

  const accountTrigger = document.querySelector(
    '[data-account-menu-trigger]',
  );

  const accountMenu = document.querySelector(
    '[data-account-menu]',
  );

  const notificationTrigger = document.querySelector(
    '[data-notification-trigger]',
  );

  const notificationPanel = document.querySelector(
    '[data-notification-panel]',
  );

  let searchTimer = null;
  let searchController = null;

  const closeAccountMenu = () => {
    if (!accountMenu || !accountTrigger) {
      return;
    }

    accountMenu.hidden = true;

    accountTrigger.setAttribute(
      'aria-expanded',
      'false',
    );
  };

  const closeNotifications = () => {
    if (
      !notificationPanel
      || !notificationTrigger
    ) {
      return;
    }

    notificationPanel.hidden = true;

    notificationTrigger.setAttribute(
      'aria-expanded',
      'false',
    );
  };

  accountTrigger?.addEventListener(
    'click',
    () => {
      const willOpen =
        accountMenu?.hidden ?? true;

      closeNotifications();

      if (!accountMenu) return;

      accountMenu.hidden = !willOpen;

      accountTrigger.setAttribute(
        'aria-expanded',
        String(willOpen),
      );
    },
  );

  notificationTrigger?.addEventListener(
    'click',
    () => {
      const willOpen =
        notificationPanel?.hidden
        ?? true;

      closeAccountMenu();

      if (!notificationPanel) {
        return;
      }

      notificationPanel.hidden =
        !willOpen;

      notificationTrigger.setAttribute(
        'aria-expanded',
        String(willOpen),
      );
    },
  );

  document.addEventListener(
    'click',
    (event) => {
      const target = event.target;

      if (!(target instanceof Node)) {
        return;
      }

      if (
        accountMenu
        && accountTrigger
        && !accountMenu.contains(target)
        && !accountTrigger.contains(target)
      ) {
        closeAccountMenu();
      }

      if (
        notificationPanel
        && notificationTrigger
        && !notificationPanel.contains(
          target,
        )
        && !notificationTrigger.contains(
          target,
        )
      ) {
        closeNotifications();
      }
    },
  );

  document.addEventListener(
    'keydown',
    (event) => {
      if (event.key !== 'Escape') {
        return;
      }

      closeAccountMenu();
      closeNotifications();

      if (searchResults) {
        searchResults.hidden = true;
      }

      searchInput?.setAttribute(
        'aria-expanded',
        'false',
      );
    },
  );

  const resultHref = (item) => {
    if (item.kind === 'professional') {
      return (
        '/profissionais/'
        + encodeURIComponent(
          item.routeId,
        )
      );
    }

    if (item.kind === 'establishment') {
      return (
        '/estabelecimentos/'
        + encodeURIComponent(
          item.routeId,
        )
      );
    }

    if (item.kind === 'experience') {
      return (
        '/experiencias/'
        + encodeURIComponent(
          item.routeId,
        )
      );
    }

    if (item.kind === 'post') {
      return (
        '/feed#post-'
        + encodeURIComponent(
          item.routeId,
        )
      );
    }

    return '/feed';
  };

  const resultKindLabel = (kind) => {
    const labels = {
      professional: 'Profissional',
      establishment: 'Estabelecimento',
      experience: 'Experiência',
      post: 'Publicação',
    };

    return labels[kind] || 'IDDUN';
  };

  const renderSearchResults = (
    items,
  ) => {
    if (!searchResults) {
      return;
    }

    searchResults.replaceChildren();

    if (!items.length) {
      const empty = (
        document.createElement('div')
      );

      empty.className =
        'feed-search-results__empty';

      empty.textContent =
        'Nenhum resultado real encontrado.';

      searchResults.appendChild(
        empty,
      );

      searchResults.hidden = false;

      searchInput?.setAttribute(
        'aria-expanded',
        'true',
      );

      return;
    }

    items
      .slice(0, 10)
      .forEach((item) => {
        const link = (
          document.createElement('a')
        );

        link.className =
          'feed-search-results__item';

        link.href = resultHref(item);
        link.setAttribute(
          'role',
          'option',
        );

        const media = (
          document.createElement('span')
        );

        media.className =
          'feed-search-results__media';

        if (item.image) {
          media.style.backgroundImage =
            `url("${item.image}")`;
        }

        const copy = (
          document.createElement('span')
        );

        const title = (
          document.createElement('strong')
        );

        title.textContent =
          item.title || 'IDDUN';

        const subtitle = (
          document.createElement('small')
        );

        const details = [
          resultKindLabel(
            item.kind,
          ),
          item.subtitle,
          item.location,
        ].filter(Boolean);

        subtitle.textContent =
          details.join(' · ');

        copy.append(
          title,
          subtitle,
        );

        link.append(
          media,
          copy,
        );

        searchResults.appendChild(
          link,
        );
      });

    searchResults.hidden = false;

    searchInput?.setAttribute(
      'aria-expanded',
      'true',
    );
  };

  const runSearch = async () => {
    if (!searchInput) return;

    const query =
      searchInput.value.trim();

    if (query.length < 2) {
      if (searchResults) {
        searchResults.hidden = true;
      }

      searchInput.setAttribute(
        'aria-expanded',
        'false',
      );

      return;
    }

    searchController?.abort();

    searchController =
      new AbortController();

    try {
      const response = await fetch(
        (
          '/api/v1/search?q='
          + encodeURIComponent(query)
          + '&limit=4'
        ),
        {
          headers: {
            Accept: 'application/json',
          },
          signal:
            searchController.signal,
        },
      );

      if (!response.ok) {
        throw new Error(
          'search_failed',
        );
      }

      const payload =
        await response.json();

      renderSearchResults(
        payload.items || [],
      );
    } catch (error) {
      if (
        error instanceof DOMException
        && error.name === 'AbortError'
      ) {
        return;
      }

      renderSearchResults([]);
    }
  };

  searchInput?.addEventListener(
    'input',
    () => {
      window.clearTimeout(
        searchTimer,
      );

      searchTimer =
        window.setTimeout(
          runSearch,
          180,
        );
    },
  );

  document.addEventListener(
    'click',
    (event) => {
      const target = event.target;

      if (
        searchRoot
        && target instanceof Node
        && !searchRoot.contains(
          target,
        )
      ) {
        if (searchResults) {
          searchResults.hidden = true;
        }

        searchInput?.setAttribute(
          'aria-expanded',
          'false',
        );
      }
    },
  );

  document.addEventListener(
    'click',
    (event) => {
      const target = event.target;

      if (
        !(target instanceof Element)
      ) {
        return;
      }

      const notificationLink =
        target.closest(
          '[data-notification-link]',
        );

      if (!notificationLink) {
        return;
      }

      const id =
        notificationLink
          .dataset
          .notificationId;

      if (!id) {
        return;
      }

      void fetch(
        (
          '/api/v1/notifications/'
          + encodeURIComponent(id)
          + '/read'
        ),
        {
          method: 'PUT',
          keepalive: true,
          credentials: 'same-origin',
          headers: {
            Accept:
              'application/json',
            'X-CSRFToken':
              window.IDDUN.csrfToken(),
          },
        },
      );
    },
  );


  // Menus "Mais" das barras Pro e Business (FE-DEC-023, 024).
  const disclosures = [
    ...document.querySelectorAll('[data-disclosure-trigger]'),
  ].map((trigger) => ({
    trigger,
    panel: document.getElementById(
      trigger.getAttribute('aria-controls') || '',
    ),
  })).filter((item) => item.panel);

  const closeDisclosures = (except) => {
    disclosures.forEach((item) => {
      if (item === except) return;
      item.panel.hidden = true;
      item.trigger.setAttribute('aria-expanded', 'false');
    });
  };

  disclosures.forEach((item) => {
    item.trigger.addEventListener('click', () => {
      const willOpen = item.panel.hidden;
      closeDisclosures(item);
      closeAccountMenu();
      item.panel.hidden = !willOpen;
      item.trigger.setAttribute('aria-expanded', String(willOpen));
      if (willOpen) item.panel.querySelector('a')?.focus();
    });
  });

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    disclosures.forEach((item) => {
      if (
        !item.panel.hidden
        && !item.panel.contains(target)
        && !item.trigger.contains(target)
      ) {
        item.panel.hidden = true;
        item.trigger.setAttribute('aria-expanded', 'false');
      }
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const open = disclosures.find((item) => !item.panel.hidden);
    closeDisclosures();
    open?.trigger.focus();
  });

  // Notificações abre o painel do feed também a partir de outras páginas
  // (#feed-notification-panel). O antigo #feed-saved-panel leva à página
  // Favoritos, que substituiu o painel (PR 2, D-SOC-07).
  const openPanelFromHash = () => {
    if (window.location.hash === '#feed-saved-panel') {
      window.location.replace('/favoritos?aba=salvos');
      return;
    }

    if (
      window.location.hash === '#feed-notification-panel'
      && notificationPanel
      && notificationTrigger
    ) {
      closeAccountMenu();
      notificationPanel.hidden = false;
      notificationTrigger.setAttribute('aria-expanded', 'true');
    }
  };

  window.addEventListener('hashchange', openPanelFromHash);
  openPanelFromHash();
})();
