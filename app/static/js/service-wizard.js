/*
 * P-002 · Wizard A. Organiza o formulário de serviço em cinco etapas.
 * Nada é enviado por este arquivo: o formulário continua sendo um único
 * POST com CSRF, validado no servidor. Sem JavaScript, todas as etapas
 * aparecem em sequência. Aqui:
 *  - uma etapa por vez, com Voltar/Continuar e progresso acessível;
 *  - avançar só com a etapa atual válida (as regras reais do formulário);
 *  - erro do servidor abre a primeira etapa com problema;
 *  - prévia lateral e revisão com os dados digitados, sem dado inventado;
 *  - prévia local da imagem escolhida (nada é enviado antes de salvar);
 *  - aviso ao sair com alterações não salvas.
 */
(() => {
  'use strict';

  const form = document.querySelector('form[data-service-wizard]');
  if (!form) return;

  const steps = Array.from(form.querySelectorAll('[data-step]'));
  const keys = steps.map((step) => step.dataset.step);
  const progress = Array.from(form.querySelectorAll('[data-progress]'));
  const back = form.querySelector('[data-wizard-back]');
  const next = form.querySelector('[data-wizard-next]');
  const submit = form.querySelector('[data-wizard-submit]');
  const status = form.querySelector('[data-wizard-status]');
  const field = (name) => form.elements.namedItem(name);
  const EMPTY = 'Ainda não informado';
  let current = 0;
  let dirty = false;
  let sending = false;

  form.classList.add('is-enhanced');
  form.setAttribute('novalidate', '');

  const controlsOf = (step) => Array.from(
    step.querySelectorAll('input:not([type="hidden"]), select, textarea'),
  );

  // Campos numéricos: o valor chega sempre com ponto ("120.5").
  const parseMoney = (value) => {
    const text = String(value || '').trim();
    if (!text) return null;
    const number = Number(text);
    return Number.isFinite(number) ? number : NaN;
  };

  const formatMoney = (value) => {
    const number = parseMoney(value);
    if (number === null || Number.isNaN(number)) return '';
    return `R$ ${number.toFixed(2).replace('.', ',')}`;
  };

  // Regras que o navegador não conhece; o servidor continua decidindo.
  const checkCustomRules = () => {
    const regular = field('regular_price');
    const price = field('price');
    if (regular && price) {
      const r = parseMoney(regular.value);
      const p = parseMoney(price.value);
      regular.setCustomValidity(Number.isNaN(r) || (r !== null && r < 0) ? 'Informe um valor válido, como 120,00.' : '');
      if (Number.isNaN(p) || (p !== null && p < 0)) {
        price.setCustomValidity('Informe um valor válido, como 100,00.');
      } else if (p !== null && r !== null && !Number.isNaN(r) && p > r) {
        price.setCustomValidity('O preço IDDUN não pode ser maior que o preço regular.');
      } else {
        price.setCustomValidity('');
      }
    }
    const image = field('image_file');
    if (image && image.files && image.files[0]) {
      const file = image.files[0];
      const max = Number(image.dataset.maxBytes || 0);
      const okType = /\.(jpe?g|png|webp)$/i.test(file.name);
      if (!okType) image.setCustomValidity('Use JPG, PNG ou WEBP.');
      else if (max && file.size > max) image.setCustomValidity('A imagem deve ter no máximo 5 MB.');
      else image.setCustomValidity('');
    } else if (image) {
      image.setCustomValidity('');
    }
  };

  const stepValid = (index) => {
    checkCustomRules();
    return controlsOf(steps[index]).every((control) => control.checkValidity());
  };

  const firstReachable = (target) => {
    for (let index = 0; index < target; index += 1) {
      if (!stepValid(index)) return index;
    }
    return target;
  };

  const announce = (text) => {
    if (status) status.textContent = text;
  };

  const render = (focus) => {
    steps.forEach((step, index) => {
      step.hidden = index !== current;
    });
    progress.forEach((item, index) => {
      const link = item.querySelector('a');
      const state = item.querySelector('[data-progress-state]');
      item.classList.toggle('is-current', index === current);
      item.classList.toggle('is-done', index < current);
      if (index === current) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
      if (state) state.textContent = index === current ? ' (etapa atual)' : index < current ? ' (concluída)' : '';
    });
    const last = current === steps.length - 1;
    back.hidden = current === 0;
    next.hidden = last;
    submit.hidden = !last;
    const title = steps[current].querySelector('.service-wizard__step-title');
    announce(`Etapa ${current + 1} de ${steps.length}: ${title ? title.textContent : ''}`);
    if (focus) {
      const legend = steps[current].querySelector('legend');
      if (legend) {
        legend.setAttribute('tabindex', '-1');
        legend.focus({ preventScroll: false });
      }
    }
  };

  const goTo = (target, focus = true) => {
    const reachable = target > current ? firstReachable(target) : target;
    if (reachable !== target) {
      current = reachable;
      render(false);
      const invalid = controlsOf(steps[current]).find((control) => !control.checkValidity());
      invalid?.reportValidity();
      invalid?.focus();
      return;
    }
    current = target;
    render(focus);
  };

  // Prévia lateral e revisão: só o que foi digitado.
  const textFor = (name) => {
    const control = field(name);
    if (!control) return '';
    if (control instanceof HTMLSelectElement) {
      return control.selectedOptions[0] ? control.selectedOptions[0].textContent.trim() : '';
    }
    if (name === 'regular_price' || name === 'price') return formatMoney(control.value);
    if (name === 'duration_minutes') return control.value.trim() ? `${control.value.trim()} min` : '';
    if (name === 'image_file') {
      if (control.files && control.files[0]) return `Nova imagem: ${control.files[0].name}`;
      return form.querySelector('[data-image-current]') ? 'Imagem atual mantida' : 'Sem imagem';
    }
    return control.value.trim();
  };

  const sync = () => {
    form.querySelectorAll('[data-review]').forEach((node) => {
      node.textContent = textFor(node.dataset.review) || node.dataset.empty || EMPTY;
    });
    form.querySelectorAll('[data-bind]').forEach((node) => {
      const value = textFor(node.dataset.bind);
      if (node.closest('[data-image-fallback]')) {
        node.textContent = value || 'Categoria';
        return;
      }
      node.textContent = value || node.dataset.empty || EMPTY;
    });
    form.querySelectorAll('[data-count]').forEach((control) => {
      const help = document.getElementById(`${control.id}-help`);
      if (help) {
        help.dataset.base = help.dataset.base || help.textContent;
        help.textContent = `${help.dataset.base} ${control.value.length}/${control.dataset.count}`;
      }
    });
  };

  // Prévia local da imagem: nada sai do aparelho antes de salvar.
  const image = field('image_file');
  const preview = form.querySelector('[data-image-preview]');
  const currentImage = form.querySelector('[data-image-current]');
  const fallback = form.querySelector('[data-image-fallback]');
  const clear = form.querySelector('[data-image-clear]');
  let previewUrl = null;
  const showImage = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    checkCustomRules();
    const file = image && image.files && image.files[0];
    const usable = file && image.checkValidity();
    if (usable) {
      previewUrl = URL.createObjectURL(file);
      preview.src = previewUrl;
    }
    preview.hidden = !usable;
    if (currentImage) currentImage.hidden = Boolean(usable);
    if (fallback) fallback.hidden = Boolean(usable);
    if (clear) clear.hidden = !file;
    if (file && !usable) image.reportValidity();
  };
  image?.addEventListener('change', showImage);
  clear?.addEventListener('click', () => {
    image.value = '';
    showImage();
    sync();
    image.focus();
  });

  form.addEventListener('input', () => {
    dirty = true;
    sync();
  });
  form.addEventListener('change', () => {
    dirty = true;
    sync();
  });

  // Enter num campo de texto avança em vez de enviar o formulário.
  form.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.defaultPrevented) return;
    const target = event.target;
    if (!(target instanceof HTMLInputElement) || target.type === 'file') return;
    if (current < steps.length - 1) {
      event.preventDefault();
      goTo(current + 1);
    }
  });

  next.addEventListener('click', () => goTo(current + 1));
  back.addEventListener('click', () => goTo(current - 1));

  form.addEventListener('click', (event) => {
    const link = event.target.closest('[data-wizard-goto]');
    if (!link) return;
    event.preventDefault();
    const index = keys.indexOf(link.dataset.wizardGoto);
    if (index >= 0) goTo(index);
  });

  form.addEventListener('submit', (event) => {
    if (sending) {
      event.preventDefault();
      return;
    }
    const broken = steps.findIndex((_, index) => !stepValid(index));
    if (broken >= 0) {
      event.preventDefault();
      current = broken;
      render(false);
      const invalid = controlsOf(steps[current]).find((control) => !control.checkValidity());
      invalid?.reportValidity();
      invalid?.focus();
      return;
    }
    sending = true;
    dirty = false;
    window.setTimeout(() => {
      submit.setAttribute('aria-busy', 'true');
      submit.setAttribute('disabled', '');
    }, 0);
  });

  window.addEventListener('pageshow', () => {
    sending = false;
    submit.removeAttribute('aria-busy');
    submit.removeAttribute('disabled');
  });

  window.addEventListener('beforeunload', (event) => {
    if (!dirty || sending) return;
    event.preventDefault();
    event.returnValue = '';
  });

  // Volta do servidor com erro: abre a primeira etapa com problema.
  const withError = steps.findIndex((step) => step.querySelector('.ds-field-errors, [aria-invalid="true"]'));
  current = withError >= 0 ? withError : 0;
  if (window.location.hash) {
    const hashed = keys.indexOf(window.location.hash.replace('#etapa-', ''));
    if (withError < 0 && hashed >= 0) current = firstReachable(hashed);
  }
  sync();
  render(withError >= 0);
  if (withError >= 0) {
    steps[current].querySelector('[aria-invalid="true"]')?.focus();
  }
})();
