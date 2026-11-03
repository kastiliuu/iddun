/*
 * Publicações (PR 3; D-SOC-11). Melhora o que já funciona sem JavaScript:
 * - compositor: miniaturas, ordem, remoção e texto alternativo por foto;
 * - carrossel: Anterior/Próxima e "1 de N";
 * - curtir pela API, sem recarregar;
 * - menu ⋯ e confirmação de Remover;
 * - janela de denúncia, que fecha sem protocolo (DEC-ID-275 B).
 * Tudo por delegação, para valer também nos cartões de "Ver mais".
 */
(() => {
  const MAX_IMAGES = 10;
  const MAX_BYTES = 5 * 1024 * 1024;
  const TYPES = ['image/jpeg', 'image/png', 'image/webp'];

  const toast = (message) => {
    const element = document.querySelector('[data-feed-toast]');
    if (!element) return;
    element.textContent = message;
    element.hidden = false;
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => { element.hidden = true; }, 2600);
  };

  /* ---------------------------------------------------------- compositor */

  const composer = document.querySelector('[data-composer-form]');

  if (composer) {
    const fileInput = composer.querySelector('[data-composer-files]');
    const thumbs = composer.querySelector('[data-composer-thumbs]');
    const caption = composer.querySelector('[data-composer-caption]');
    const count = composer.querySelector('[data-composer-count]');
    const author = composer.querySelector('[data-composer-author]');
    const service = composer.querySelector('[data-composer-service]');
    const errorBox = composer.querySelector('[data-composer-error]');
    const submit = composer.querySelector('[data-composer-submit]');
    let items = [];

    const showError = (message) => {
      errorBox.textContent = message;
      errorBox.hidden = !message;
    };

    const syncService = () => {
      if (!service) return;
      const select = service.querySelector('select');
      const value = author.value;
      let visible = 0;
      [...select.options].forEach((option) => {
        if (!option.value) return;
        const matches = option.dataset.author === value;
        option.hidden = !matches;
        option.disabled = !matches;
        if (matches) visible += 1;
      });
      if (select.selectedOptions[0]?.disabled) select.value = '';
      service.hidden = visible === 0;
    };

    const render = () => {
      thumbs.replaceChildren();
      thumbs.hidden = items.length === 0;
      items.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'post-composer__thumb';

        const img = document.createElement('img');
        img.src = item.url;
        img.alt = '';
        li.append(img);

        const alt = document.createElement('input');
        alt.type = 'text';
        alt.maxLength = 300;
        alt.value = item.alt;
        alt.placeholder = 'Descreva a foto';
        alt.setAttribute('aria-label', `Texto alternativo da foto ${index + 1}`);
        alt.addEventListener('input', () => { item.alt = alt.value; });
        li.append(alt);

        const controls = document.createElement('div');
        controls.className = 'post-composer__thumb-controls';
        const button = (label, text, disabled, action) => {
          const element = document.createElement('button');
          element.type = 'button';
          element.textContent = text;
          element.setAttribute('aria-label', label);
          element.disabled = disabled;
          element.addEventListener('click', action);
          return element;
        };
        controls.append(
          button(`Mover foto ${index + 1} para antes`, '←', index === 0, () => {
            [items[index - 1], items[index]] = [items[index], items[index - 1]];
            render();
          }),
          button(`Mover foto ${index + 1} para depois`, '→', index === items.length - 1, () => {
            [items[index + 1], items[index]] = [items[index], items[index + 1]];
            render();
          }),
          button(`Remover foto ${index + 1}`, '✕', false, () => {
            URL.revokeObjectURL(item.url);
            items.splice(index, 1);
            render();
          }),
        );
        li.append(controls);
        thumbs.append(li);
      });
    };

    fileInput.addEventListener('change', () => {
      const chosen = [...fileInput.files];
      fileInput.value = '';
      let message = '';
      chosen.forEach((file) => {
        if (items.length >= MAX_IMAGES) {
          message = `Uma publicação pode ter até ${MAX_IMAGES} fotos.`;
        } else if (!TYPES.includes(file.type)) {
          message = 'Use fotos JPG, PNG ou WebP.';
        } else if (file.size > MAX_BYTES) {
          message = 'Cada foto deve ter no máximo 5 MB.';
        } else {
          items.push({ file, url: URL.createObjectURL(file), alt: '' });
        }
      });
      showError(message);
      render();
    });

    caption.addEventListener('input', () => {
      count.textContent = String(caption.value.length);
    });
    author.addEventListener('change', syncService);
    syncService();

    composer.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!caption.value.trim() && items.length === 0) {
        showError('Escreva um texto ou adicione uma foto.');
        caption.focus();
        return;
      }

      const data = new FormData(composer);
      data.delete('images');
      items.forEach((item) => {
        data.append('images', item.file, item.file.name);
        data.append('alt_texts', item.alt);
      });

      submit.disabled = true;
      submit.textContent = 'Publicando…';
      try {
        const response = await window.IDDUN.fetchWithCsrf(composer.action, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: data,
        });
        if (response.status === 413) throw new Error('Cada foto deve ter no máximo 5 MB.');
        const payload = await response.json();
        if (!payload.redirect) throw new Error('publish_failed');
        // A rota guarda a mensagem e diz para onde ir (o post ou o erro).
        // Na mesma página, troca só a âncora e recarrega uma vez.
        const target = new URL(payload.redirect, window.location.href);
        if (
          target.pathname === window.location.pathname
          && target.search === window.location.search
        ) {
          window.location.hash = target.hash;
          window.location.reload();
        } else {
          window.location.assign(target.href);
        }
      } catch (error) {
        showError(
          error.message && !error.message.includes('_')
            ? error.message
            : 'Não foi possível publicar agora. Tente de novo.',
        );
        submit.disabled = false;
        submit.textContent = 'Publicar';
      }
    });
  }

  /* ----------------------------------------------------------- carrossel */

  const slideWidth = (track) => track.querySelector('[data-carousel-slide]')?.clientWidth || track.clientWidth;

  const updateCount = (carousel) => {
    const track = carousel.querySelector('[data-carousel-track]');
    const label = carousel.querySelector('[data-carousel-count]');
    if (!track || !label) return;
    const total = track.querySelectorAll('[data-carousel-slide]').length;
    const index = Math.min(total, Math.round(track.scrollLeft / slideWidth(track)) + 1);
    label.textContent = `${index} de ${total}`;
    carousel.querySelector('[data-carousel-prev]').disabled = index <= 1;
    carousel.querySelector('[data-carousel-next]').disabled = index >= total;
  };

  document.querySelectorAll('[data-carousel]').forEach(updateCount);

  document.addEventListener('scroll', (event) => {
    const track = event.target;
    if (track instanceof Element && track.matches('[data-carousel-track]')) {
      window.clearTimeout(track.countTimer);
      track.countTimer = window.setTimeout(() => updateCount(track.closest('[data-carousel]')), 80);
    }
  }, true);

  document.addEventListener('keydown', (event) => {
    const track = event.target;
    if (!(track instanceof Element) || !track.matches('[data-carousel-track]')) return;
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    track.scrollBy({ left: (event.key === 'ArrowRight' ? 1 : -1) * slideWidth(track), behavior: 'smooth' });
  });

  /* --------------------------------------------------- menus e denúncia */

  const dialog = document.querySelector('[data-report-dialog]');
  let reportReturn = null;

  const closeMenus = (except) => {
    document.querySelectorAll('[data-post-menu-trigger][aria-expanded="true"]').forEach((trigger) => {
      if (trigger === except) return;
      trigger.setAttribute('aria-expanded', 'false');
      const panel = document.getElementById(trigger.getAttribute('aria-controls'));
      if (panel) panel.hidden = true;
    });
  };

  const openReport = (button) => {
    if (!dialog) return;
    dialog.querySelector('[data-report-type]').value = button.dataset.targetType;
    dialog.querySelector('[data-report-id]').value = button.dataset.targetId;
    dialog.querySelector('form').reset();
    dialog.querySelector('[data-report-type]').value = button.dataset.targetType;
    dialog.querySelector('[data-report-id]').value = button.dataset.targetId;
    reportReturn = button.closest('[data-post-menu]')?.querySelector('[data-post-menu-trigger]') || button;
    closeMenus();
    dialog.showModal();
    dialog.querySelector('input[name="category"]').focus();
  };

  const closeReport = () => {
    dialog.close();
    reportReturn?.focus();
  };

  if (dialog) {
    dialog.querySelector('[data-report-cancel]').addEventListener('click', closeReport);
    dialog.querySelector('[data-report-form]').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      try {
        const response = await window.IDDUN.fetchWithCsrf(form.action, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: new FormData(form),
        });
        if (!response.ok && response.status !== 204) throw new Error('report_failed');
        // DEC-ID-275 B: sem protocolo nem confirmação; a janela só fecha.
        closeReport();
      } catch {
        toast('Não foi possível enviar agora. Tente de novo.');
      }
    });
  }

  const setLiked = (button, liked, total) => {
    button.setAttribute('aria-pressed', String(liked));
    button.classList.toggle('is-active', liked);
    button.dataset.active = String(liked);
    const next = button.closest('form')?.querySelector('[data-like-next]');
    if (next) next.value = liked ? 'false' : 'true';
    const counter = button.querySelector('[data-like-count]');
    if (counter && Number.isFinite(total)) counter.textContent = String(total);
  };

  const like = async (button) => {
    if (button.dataset.loginUrl) {
      window.location.assign(button.dataset.loginUrl);
      return;
    }
    const liked = button.getAttribute('aria-pressed') !== 'true';
    const counter = button.querySelector('[data-like-count]');
    const before = Number(counter?.textContent || 0);
    setLiked(button, liked, before + (liked ? 1 : -1));
    button.disabled = true;
    try {
      const response = await window.IDDUN.fetchWithCsrf(
        `/api/v1/posts/${encodeURIComponent(button.dataset.postId)}/like`,
        { method: liked ? 'PUT' : 'DELETE' },
      );
      if (!response.ok) throw new Error('like_failed');
      const payload = await response.json();
      setLiked(button, payload.liked, payload.likesCount);
    } catch {
      setLiked(button, !liked, before);
      toast('Não foi possível curtir agora. Tente de novo.');
    } finally {
      button.disabled = false;
    }
  };

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const likeButton = target.closest('[data-like-button]');
    if (likeButton) {
      event.preventDefault();
      void like(likeButton);
      return;
    }

    const prev = target.closest('[data-carousel-prev], [data-carousel-next]');
    if (prev) {
      const track = prev.closest('[data-carousel]').querySelector('[data-carousel-track]');
      const direction = prev.hasAttribute('data-carousel-next') ? 1 : -1;
      track.scrollBy({ left: direction * slideWidth(track), behavior: 'smooth' });
      return;
    }

    const trigger = target.closest('[data-post-menu-trigger]');
    if (trigger) {
      const panel = document.getElementById(trigger.getAttribute('aria-controls'));
      const open = trigger.getAttribute('aria-expanded') !== 'true';
      closeMenus(trigger);
      trigger.setAttribute('aria-expanded', String(open));
      panel.hidden = !open;
      if (open) panel.querySelector('button, a')?.focus();
      return;
    }

    const ask = target.closest('[data-post-remove-ask]');
    if (ask) {
      const confirm = ask.parentElement.querySelector('[data-post-remove-confirm]');
      confirm.hidden = false;
      confirm.querySelector('button').focus();
      return;
    }

    const report = target.closest('[data-report-open]');
    if (report) {
      openReport(report);
      return;
    }

    if (!target.closest('[data-post-menu]')) closeMenus();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const open = document.querySelector('[data-post-menu-trigger][aria-expanded="true"]');
    if (open) {
      closeMenus();
      open.focus();
    }
  });
})();
