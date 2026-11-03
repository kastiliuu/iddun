(() => {
  const toast = document.querySelector(
    '[data-feed-toast]',
  );

  const grid = document.querySelector(
    '[data-feed-grid]',
  );

  const loadMoreButton = document.querySelector(
    '[data-feed-load-more]',
  );

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
      const response = await window.IDDUN.fetchWithCsrf(
        endpoint,
        {
          method:
            nextPressed
              ? 'PUT'
              : 'DELETE',
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
