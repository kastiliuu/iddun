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

  const savedTriggers = [
    ...document.querySelectorAll(
      '[data-saved-trigger]',
    ),
  ];

  const savedPanel = document.querySelector(
    '[data-saved-panel]',
  );

  const toast = document.querySelector(
    '[data-feed-toast]',
  );

  const grid = document.querySelector(
    '[data-feed-grid]',
  );

  const loadMoreButton = document.querySelector(
    '[data-feed-load-more]',
  );

  let searchTimer = null;
  let searchController = null;
  let toastTimer = null;

  const showToast = (message) => {
    if (!toast) return;

    toast.textContent = message;
    toast.hidden = false;

    window.clearTimeout(
      toastTimer,
    );

    toastTimer = window.setTimeout(
      () => {
        toast.hidden = true;
      },
      2600,
    );
  };

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

  const closeSaved = () => {
    if (!savedPanel) {
      return;
    }

    savedPanel.hidden = true;

    savedTriggers.forEach(
      (trigger) => {
        trigger.setAttribute(
          'aria-expanded',
          'false',
        );
      },
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
      closeSaved();

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
      closeSaved();

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

  savedTriggers.forEach(
    (trigger) => {
      trigger.addEventListener(
        'click',
        () => {
          const willOpen =
            savedPanel?.hidden
            ?? true;

          closeAccountMenu();
          closeNotifications();

          if (!savedPanel) {
            return;
          }

          savedPanel.hidden =
            !willOpen;

          savedTriggers.forEach(
            (item) => {
              item.setAttribute(
                'aria-expanded',
                String(willOpen),
              );
            },
          );
        },
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

      if (
        savedPanel
        && !savedPanel.contains(
          target,
        )
        && !savedTriggers.some(
          (trigger) => (
            trigger.contains(target)
          ),
        )
      ) {
        closeSaved();
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
      closeSaved();

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
          headers: {
            Accept:
              'application/json',
          },
        },
      );
    },
  );

  const setPressedState = (
    button,
    pressed,
    type,
  ) => {
    button.setAttribute(
      'aria-pressed',
      String(pressed),
    );

    button.classList.toggle(
      'is-active',
      pressed,
    );

    if (type === 'follow') {
      button.textContent = (
        pressed
          ? 'Seguindo'
          : 'Seguir'
      );
    } else {
      button.setAttribute(
        'aria-label',
        (
          pressed
            ? 'Remover dos salvos'
            : 'Salvar publicação'
        ),
      );
    }
  };

  const graphMutation = async (
    button,
    type,
  ) => {
    if (button.disabled) {
      return;
    }

    const targetType =
      button.dataset.targetType;

    const targetId =
      button.dataset.targetId;

    if (!targetType || !targetId) {
      return;
    }

    const pressed = (
      button.getAttribute(
        'aria-pressed',
      ) === 'true'
    );

    const nextPressed = !pressed;

    const segment = (
      type === 'follow'
        ? 'follows'
        : 'saves'
    );

    const endpoint = (
      '/api/v1/graph/'
      + segment
      + '/'
      + encodeURIComponent(
        targetType,
      )
      + '/'
      + encodeURIComponent(
        targetId,
      )
    );

    setPressedState(
      button,
      nextPressed,
      type,
    );

    button.disabled = true;

    try {
      const response = await fetch(
        endpoint,
        {
          method:
            nextPressed
              ? 'PUT'
              : 'DELETE',
          headers: {
            Accept: 'application/json',
          },
        },
      );

      if (!response.ok) {
        throw new Error(
          'graph_mutation_failed',
        );
      }

      showToast(
        type === 'follow'
          ? (
              nextPressed
                ? 'Perfil adicionado à sua rede.'
                : 'Perfil removido da sua rede.'
            )
          : (
              nextPressed
                ? 'Publicação salva.'
                : 'Publicação removida dos salvos.'
            ),
      );

      if (type === 'follow') {
        document
          .querySelectorAll(
            (
              '[data-follow-button]'
              + `[data-target-type="${CSS.escape(targetType)}"]`
              + `[data-target-id="${CSS.escape(targetId)}"]`
            ),
          )
          .forEach((item) => {
            if (
              item instanceof
              HTMLButtonElement
            ) {
              setPressedState(
                item,
                nextPressed,
                'follow',
              );
            }
          });
      }
    } catch {
      setPressedState(
        button,
        pressed,
        type,
      );

      showToast(
        'Não foi possível atualizar agora. Tente novamente.',
      );
    } finally {
      button.disabled = false;
    }
  };

  document.addEventListener(
    'click',
    (event) => {
      const target = event.target;

      if (
        !(target instanceof Element)
      ) {
        return;
      }

      const saveButton =
        target.closest(
          '[data-save-button]',
        );

      if (
        saveButton instanceof
        HTMLButtonElement
      ) {
        void graphMutation(
          saveButton,
          'save',
        );

        return;
      }

      const followButton =
        target.closest(
          '[data-follow-button]',
        );

      if (
        followButton instanceof
        HTMLButtonElement
      ) {
        void graphMutation(
          followButton,
          'follow',
        );

        return;
      }

      const shareButton =
        target.closest(
          '[data-share-button]',
        );

      if (
        shareButton instanceof
        HTMLButtonElement
      ) {
        const url =
          shareButton.dataset.shareUrl;

        const title =
          shareButton.dataset.shareTitle
          || 'IDDUN';

        if (!url) return;

        if (navigator.share) {
          void navigator
            .share({
              title,
              url,
            })
            .catch(() => {});
        } else if (
          navigator.clipboard
          && window.isSecureContext
        ) {
          void navigator.clipboard
            .writeText(url)
            .then(() => {
              showToast(
                'Link copiado.',
              );
            })
            .catch(() => {
              showToast(
                'Não foi possível copiar o link.',
              );
            });
        } else {
          window.prompt(
            'Copie o link:',
            url,
          );
        }
      }
    },
  );

  const loadMore = async () => {
    if (
      !loadMoreButton
      || !grid
      || loadMoreButton.disabled
    ) {
      return;
    }

    const cursor =
      loadMoreButton.dataset.nextCursor;

    const mode =
      grid.dataset.feedMode
      || 'for-you';

    if (!cursor) {
      loadMoreButton.hidden = true;
      return;
    }

    loadMoreButton.disabled = true;

    const originalText =
      loadMoreButton.textContent;

    loadMoreButton.textContent =
      'Carregando...';

    try {
      const params =
        new URLSearchParams({
          mode,
          cursor,
        });

      const response = await fetch(
        '/feed/mais?'
        + params.toString(),
        {
          headers: {
            Accept: 'application/json',
          },
        },
      );

      if (!response.ok) {
        throw new Error(
          'pagination_failed',
        );
      }

      const payload =
        await response.json();

      if (payload.html) {
        grid.insertAdjacentHTML(
          'beforeend',
          payload.html,
        );
      }

      const nextCursor =
        payload.nextCursor || '';

      grid.dataset.nextCursor =
        nextCursor;

      loadMoreButton.dataset.nextCursor =
        nextCursor;

      if (!nextCursor) {
        loadMoreButton.hidden = true;
      }
    } catch {
      showToast(
        'Não foi possível carregar mais trabalhos.',
      );
    } finally {
      loadMoreButton.disabled = false;

      if (!loadMoreButton.hidden) {
        loadMoreButton.textContent =
          originalText;
      }
    }
  };

  loadMoreButton?.addEventListener(
    'click',
    () => {
      void loadMore();
    },
  );

  if (window.location.hash) {
    const target = document.querySelector(
      window.location.hash,
    );

    if (target) {
      window.requestAnimationFrame(
        () => {
          target.scrollIntoView({
            block: 'center',
          });
        },
      );
    }
  }
})();
