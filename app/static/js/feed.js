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

  // Seguir e salvar ficam em graph.js, igual em todas as páginas (PR 2).

  document.addEventListener(
    'click',
    (event) => {
      const target = event.target;

      if (
        !(target instanceof Element)
      ) {
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
