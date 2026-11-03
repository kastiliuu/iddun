/*
 * Seguir e salvar em qualquer página (PR 2, D-SOC-05).
 *
 * Botões:
 *   [data-follow-button] ou [data-save-button]
 *   data-target-type, data-target-id  — alvo na API /api/v1/graph
 *   data-login-url                    — visitante vai ao login e volta
 *   data-save-title (opcional)        — nome no rótulo do salvar
 *   [data-graph-label] (filho)        — onde escrever Seguir/Seguindo
 *
 * Contadores: [data-follower-count] com o mesmo tipo e id do alvo.
 * Tudo grava na conta; nada fica só no navegador.
 */
(() => {
  const LEGACY_KEYS = [
    'iddun:favorites:v2',
    'iddun:favorites:v1',
  ];

  const authenticated =
    document.body.dataset.authenticated === 'true';

  const reduceMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)',
  ).matches;

  let toastTimer = null;

  const toastElement = () => {
    let element = document.querySelector('[data-feed-toast]');

    if (!element) {
      element = document.createElement('div');
      element.className = 'feed-toast';
      element.setAttribute('role', 'status');
      element.setAttribute('aria-live', 'polite');
      element.dataset.feedToast = '';
      element.hidden = true;
      document.body.append(element);
    }

    return element;
  };

  const showToast = (message) => {
    const element = toastElement();
    element.textContent = message;
    element.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      element.hidden = true;
    }, 2600);
  };

  const kindOf = (button) => (
    button.hasAttribute('data-follow-button') ? 'follow' : 'save'
  );

  const sameTarget = (kind, targetType, targetId) => document.querySelectorAll(
    (kind === 'follow' ? '[data-follow-button]' : '[data-save-button]')
    + `[data-target-type="${CSS.escape(targetType)}"]`
    + `[data-target-id="${CSS.escape(targetId)}"]`,
  );

  const saveLabel = (button, pressed) => {
    const title = button.dataset.saveTitle;

    if (!title) {
      return pressed ? 'Remover dos salvos' : 'Salvar publicação';
    }

    return pressed ? `Remover ${title} dos favoritos` : `Salvar ${title}`;
  };

  const setPressed = (button, pressed) => {
    button.setAttribute('aria-pressed', String(pressed));
    button.dataset.active = String(pressed);
    button.classList.toggle('is-active', pressed);

    if (kindOf(button) === 'follow') {
      const label = button.querySelector('[data-graph-label]') || button;
      label.textContent = pressed ? 'Seguindo' : 'Seguir';
    } else {
      button.setAttribute('aria-label', saveLabel(button, pressed));
    }
  };

  const updateFollowerCount = (targetType, targetId, delta) => {
    document
      .querySelectorAll(
        '[data-follower-count]'
        + `[data-target-type="${CSS.escape(targetType)}"]`
        + `[data-target-id="${CSS.escape(targetId)}"]`,
      )
      .forEach((element) => {
        const next = Math.max(0, Number(element.dataset.count || 0) + delta);
        element.dataset.count = String(next);
        element.textContent = next === 1 ? '1 seguidor' : `${next} seguidores`;
      });
  };

  const pop = (button) => {
    if (reduceMotion || !button.hasAttribute('data-pop')) return;
    button.classList.remove('is-popping');
    void button.offsetWidth;
    button.classList.add('is-popping');
    button.addEventListener('animationend', () => {
      button.classList.remove('is-popping');
    }, { once: true });
  };

  const goToLogin = (button) => {
    const fallback = `/login?next=${encodeURIComponent(
      window.location.pathname + window.location.search + window.location.hash,
    )}`;
    window.location.assign(button.dataset.loginUrl || fallback);
  };

  const successMessage = (kind, targetType, pressed) => {
    if (kind === 'follow') {
      return pressed ? 'Perfil adicionado à sua rede.' : 'Perfil removido da sua rede.';
    }

    if (targetType === 'work_post') {
      return pressed ? 'Publicação salva.' : 'Publicação removida dos salvos.';
    }

    return pressed ? 'Salvo em Favoritos.' : 'Removido de Favoritos.';
  };

  const mutate = async (button) => {
    if (button.disabled) return;

    const kind = kindOf(button);
    const { targetType, targetId } = button.dataset;

    if (!targetType || !targetId) return;

    if (!authenticated) {
      goToLogin(button);
      return;
    }

    const pressed = button.getAttribute('aria-pressed') === 'true';
    const next = !pressed;
    const endpoint = (
      `/api/v1/graph/${kind === 'follow' ? 'follows' : 'saves'}/`
      + `${encodeURIComponent(targetType)}/${encodeURIComponent(targetId)}`
    );

    setPressed(button, next);
    button.disabled = true;

    try {
      const response = await window.IDDUN.fetchWithCsrf(endpoint, {
        method: next ? 'PUT' : 'DELETE',
      });

      if (response.status === 401) {
        goToLogin(button);
        return;
      }

      if (!response.ok) {
        let message = 'Não foi possível atualizar agora. Tente novamente.';
        try {
          const payload = await response.json();
          if (payload?.error?.code === 'own_profile') message = payload.error.message;
        } catch {
          // Mantém a mensagem padrão.
        }
        throw new Error(message);
      }

      sameTarget(kind, targetType, targetId).forEach((item) => {
        setPressed(item, next);
      });

      if (kind === 'follow') {
        updateFollowerCount(targetType, targetId, next ? 1 : -1);
      } else if (next) {
        pop(button);
      }

      showToast(successMessage(kind, targetType, next));
      document.dispatchEvent(new CustomEvent('iddun:graph-change', {
        detail: { kind, targetType, targetId, active: next },
      }));
    } catch (error) {
      setPressed(button, pressed);
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  };

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const button = target.closest('[data-follow-button], [data-save-button]');
    if (!(button instanceof HTMLButtonElement)) return;

    // Os botões ficam sobre cartões clicáveis; o clique não abre o cartão.
    event.preventDefault();
    event.stopPropagation();
    void mutate(button);
  }, true);

  // Favoritos que a versão anterior guardava só neste navegador vão para a
  // conta uma vez; depois as chaves locais são apagadas.
  const migrateLegacyFavorites = async () => {
    if (!authenticated) return;

    let slugs = [];
    try {
      LEGACY_KEYS.forEach((key) => {
        const parsed = JSON.parse(window.localStorage.getItem(key) || '[]');
        if (Array.isArray(parsed)) {
          parsed.forEach((slug) => {
            if (typeof slug === 'string' && slug && !slugs.includes(slug)) slugs.push(slug);
          });
        }
      });
    } catch {
      return;
    }

    slugs = slugs.slice(0, 200);
    if (!slugs.length) return;

    try {
      const response = await window.IDDUN.fetchWithCsrf('/api/v1/graph/reconcile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ follows: [], saves: [], experienceSlugs: slugs }),
      });

      if (!response.ok) return;

      const payload = await response.json();
      LEGACY_KEYS.forEach((key) => window.localStorage.removeItem(key));

      (payload?.imported?.saves || []).forEach((item) => {
        sameTarget('save', item.targetType, String(item.targetId)).forEach((button) => {
          setPressed(button, true);
        });
      });
    } catch {
      // Tenta de novo na próxima página.
    }
  };

  void migrateLegacyFavorites();
})();
