(() => {
  const modeCards = document.querySelectorAll('[data-mode-card]');
  modeCards.forEach((card) => {
    card.addEventListener('click', () => {
      const input = card.querySelector('input[type="radio"]');
      if (input) input.checked = true;
    });
  });

  document.querySelectorAll('[data-image-upload]').forEach((wrapper) => {
    const input = wrapper.querySelector('[data-image-input]');
    const preview = wrapper.querySelector('[data-image-preview]');
    if (!input || !preview) return;

    input.addEventListener('change', () => {
      const file = input.files?.[0];
      if (!file) return;
      if (preview.dataset.previewUrl) URL.revokeObjectURL(preview.dataset.previewUrl);
      const url = URL.createObjectURL(file);
      preview.dataset.previewUrl = url;
      preview.style.backgroundImage = `url("${url}")`;
      preview.classList.add('has-image');
      wrapper.closest('[data-media-control]')?.querySelector('[data-focus-control]')?.removeAttribute('hidden');
    });
  });

  document.querySelectorAll('[data-media-control]').forEach((control) => {
    const preview = control.querySelector('[data-image-preview]');
    const hiddenX = control.querySelector('[data-focus-x]');
    const hiddenY = control.querySelector('[data-focus-y]');
    const rangeX = control.querySelector('[data-focus-range-x]');
    const rangeY = control.querySelector('[data-focus-range-y]');
    if (!preview || !hiddenX || !hiddenY || !rangeX || !rangeY) return;

    const updateFocus = () => {
      hiddenX.value = rangeX.value;
      hiddenY.value = rangeY.value;
      preview.style.backgroundPosition = `${rangeX.value}% ${rangeY.value}%`;
    };
    rangeX.addEventListener('input', updateFocus);
    rangeY.addEventListener('input', updateFocus);
    updateFocus();
  });

  document.querySelectorAll('[data-multi-upload]').forEach((wrapper) => {
    const input = wrapper.querySelector('[data-multi-input]');
    const preview = wrapper.parentElement?.querySelector('[data-multi-preview]');
    if (!input || !preview) return;

    input.addEventListener('change', () => {
      preview.querySelectorAll('img').forEach((image) => {
        if (image.dataset.previewUrl) URL.revokeObjectURL(image.dataset.previewUrl);
      });
      preview.innerHTML = '';
      [...(input.files || [])].slice(0, 10).forEach((file) => {
        const image = document.createElement('img');
        image.alt = 'Prévia da imagem selecionada';
        image.dataset.previewUrl = URL.createObjectURL(file);
        image.src = image.dataset.previewUrl;
        preview.appendChild(image);
      });
    });
  });

  const form = document.querySelector('[data-wizard-form]');
  if (!form) return;

  const total = Number(form.dataset.wizardTotal || 1);
  const steps = [...form.querySelectorAll('[data-wizard-step]')];
  const navItems = [...document.querySelectorAll('[data-step-nav]')];
  const previous = form.querySelector('[data-wizard-prev]');
  const next = form.querySelector('[data-wizard-next]');
  const submit = form.querySelector('[data-wizard-submit]');
  const progress = document.querySelector('[data-wizard-progress]');
  const progressLabel = document.querySelector('[data-wizard-progress-label]');
  let current = 1;

  const focusFirst = (step) => {
    const first = step.querySelector('input:not([type="hidden"]), select, textarea, button');
    if (first && window.matchMedia('(min-width: 761px)').matches) {
      window.requestAnimationFrame(() => first.focus({ preventScroll: true }));
    }
  };

  const render = () => {
    steps.forEach((step) => {
      const active = Number(step.dataset.wizardStep) === current;
      step.hidden = !active;
      step.classList.toggle('is-active', active);
      if (active) focusFirst(step);
    });

    navItems.forEach((item) => {
      const index = Number(item.dataset.stepNav);
      item.classList.toggle('is-active', index === current);
      item.classList.toggle('is-complete', index < current);
    });

    const percentage = Math.round((current / total) * 100);
    if (progress) progress.style.width = `${percentage}%`;
    if (progressLabel) progressLabel.textContent = `${percentage}%`;
    if (previous) previous.hidden = current === 1;
    if (next) next.hidden = current === total;
    if (submit) submit.hidden = current !== total;

    const activeStep = steps.find((step) => Number(step.dataset.wizardStep) === current);
    activeStep?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  const validateStep = () => {
    const activeStep = steps.find((step) => Number(step.dataset.wizardStep) === current);
    if (!activeStep) return true;
    const required = [...activeStep.querySelectorAll('[required]')];
    for (const field of required) {
      if (!field.checkValidity()) {
        field.reportValidity();
        return false;
      }
    }
    return true;
  };

  next?.addEventListener('click', () => {
    if (!validateStep()) return;
    if (current < total) {
      current += 1;
      render();
    }
  });

  previous?.addEventListener('click', () => {
    if (current > 1) {
      current -= 1;
      render();
    }
  });

  navItems.forEach((item) => {
    item.addEventListener('click', () => {
      const target = Number(item.dataset.stepNav);
      if (target <= current) {
        current = target;
        render();
      }
    });
  });

  const hasServerErrors = form.querySelector('.field-errors, .form-error, [aria-invalid="true"]');
  if (hasServerErrors) {
    const errorStep = hasServerErrors.closest('[data-wizard-step]');
    if (errorStep) current = Number(errorStep.dataset.wizardStep) || 1;
  }

  render();
})();
