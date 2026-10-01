(() => {
  const megabyte = 1024 * 1024;
  const maxImageBytes = (
    5 * megabyte
  );
  const maxMultiUploadBytes = (
    30 * megabyte
  );

  const allowedImageTypes = new Set([
    'image/jpeg',
    'image/png',
    'image/webp',
  ]);

  const allowedImageExtension = (
    /\.(jpe?g|png|webp)$/i
  );

  const selectedFiles = (input) => (
    [...(input.files || [])]
  );

  const errorIdFor = (input) => (
    `${input.id || input.name}-client-error`
  );

  const errorHostFor = (input) => (
    input.closest('.platform-field')
    || input.parentElement
  );

  const clearFileError = (input) => {
    const errorId = errorIdFor(input);

    document
      .getElementById(errorId)
      ?.remove();

    input.removeAttribute(
      'aria-invalid',
    );

    const describedBy = (
      input.getAttribute(
        'aria-describedby',
      )
      || ''
    )
      .split(/\s+/)
      .filter(
        (value) => (
          value
          && value !== errorId
        ),
      );

    if (describedBy.length) {
      input.setAttribute(
        'aria-describedby',
        describedBy.join(' '),
      );
    } else {
      input.removeAttribute(
        'aria-describedby',
      );
    }
  };

  const showFileError = (
    input,
    message,
    moveToError = false,
  ) => {
    clearFileError(input);

    const errorHost = (
      errorHostFor(input)
    );

    if (!errorHost) return false;

    const errorId = errorIdFor(input);
    const errorList = (
      document.createElement('ul')
    );
    const errorItem = (
      document.createElement('li')
    );

    errorList.id = errorId;
    errorList.className = (
      'field-errors '
      + 'platform-client-errors'
    );
    errorList.dataset.clientFileError = '';

    errorList.setAttribute(
      'role',
      'alert',
    );

    errorItem.textContent = message;
    errorList.appendChild(errorItem);
    errorHost.appendChild(errorList);

    input.setAttribute(
      'aria-invalid',
      'true',
    );

    const describedBy = new Set(
      (
        input.getAttribute(
          'aria-describedby',
        )
        || ''
      )
        .split(/\s+/)
        .filter(Boolean),
    );

    describedBy.add(errorId);

    input.setAttribute(
      'aria-describedby',
      [...describedBy].join(' '),
    );

    if (moveToError) {
      errorList.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }

    return false;
  };

  const uploadRulesFor = (input) => {
    if (
      !input.matches(
        '[data-multi-input]',
      )
    ) {
      return {
        minimum: 0,
        maximum: 1,
        maxTotalBytes:
          maxImageBytes,
      };
    }

    const isOnboarding = Boolean(
      input.closest(
        '[data-wizard-form]',
      ),
    );

    const isPortfolio = (
      input.name
      === 'portfolio_files'
    );

    return {
      minimum:
        isOnboarding
        && isPortfolio
          ? 3
          : 0,
      maximum:
        isPortfolio
          ? 8
          : 10,
      maxTotalBytes:
        maxMultiUploadBytes,
    };
  };

  const validateImageInput = (
    input,
    moveToError = false,
  ) => {
    const files = (
      selectedFiles(input)
    );

    const rules = (
      uploadRulesFor(input)
    );

    if (
      files.length
      < rules.minimum
    ) {
      return showFileError(
        input,
        (
          `Selecione pelo menos `
          + `${rules.minimum} imagens `
          + `para continuar.`
        ),
        moveToError,
      );
    }

    if (
      files.length
      > rules.maximum
    ) {
      return showFileError(
        input,
        (
          `Selecione no máximo `
          + `${rules.maximum} imagens `
          + `por envio.`
        ),
        moveToError,
      );
    }

    const invalidType = files.find(
      (file) => (
        !allowedImageExtension.test(
          file.name,
        )
        || (
          file.type
          && !allowedImageTypes.has(
            file.type,
          )
        )
      ),
    );

    if (invalidType) {
      return showFileError(
        input,
        (
          `“${invalidType.name}” `
          + `não é uma imagem JPG, `
          + `PNG ou WEBP.`
        ),
        moveToError,
      );
    }

    const oversized = files.find(
      (file) => (
        file.size
        > maxImageBytes
      ),
    );

    if (oversized) {
      return showFileError(
        input,
        (
          `“${oversized.name}” `
          + `ultrapassa o limite `
          + `de 5 MB.`
        ),
        moveToError,
      );
    }

    const totalBytes = files.reduce(
      (total, file) => (
        total + file.size
      ),
      0,
    );

    if (
      totalBytes
      > rules.maxTotalBytes
    ) {
      return showFileError(
        input,
        (
          'A seleção pode ter '
          + 'no máximo 30 MB '
          + 'no total.'
        ),
        moveToError,
      );
    }

    clearFileError(input);

    return true;
  };

  const modeCards = (
    document.querySelectorAll(
      '[data-mode-card]',
    )
  );

  modeCards.forEach((card) => {
    card.addEventListener(
      'click',
      () => {
        const input = card.querySelector(
          'input[type="radio"]',
        );

        if (input) {
          input.checked = true;
        }
      },
    );
  });

  document
    .querySelectorAll(
      '[data-image-upload]',
    )
    .forEach((wrapper) => {
      const input = wrapper.querySelector(
        '[data-image-input]',
      );

      const preview = wrapper.querySelector(
        '[data-image-preview]',
      );

      if (
        !input
        || !preview
      ) {
        return;
      }

      input.addEventListener(
        'change',
        () => {
          const file = (
            selectedFiles(input)[0]
          );

          if (!file) {
            clearFileError(input);
            return;
          }

          if (
            !validateImageInput(input)
          ) {
            input.value = '';
            return;
          }

          if (
            preview.dataset.previewUrl
          ) {
            URL.revokeObjectURL(
              preview.dataset.previewUrl,
            );
          }

          const url = (
            URL.createObjectURL(file)
          );

          preview.dataset.previewUrl = (
            url
          );

          preview.style.backgroundImage = (
            `url("${url}")`
          );

          preview.classList.add(
            'has-image',
          );
        },
      );
    });

  const clearMultiPreview = (
    preview,
  ) => {
    preview
      .querySelectorAll('img')
      .forEach((image) => {
        if (
          image.dataset.previewUrl
        ) {
          URL.revokeObjectURL(
            image.dataset.previewUrl,
          );
        }
      });

    preview.replaceChildren();
  };

  document
    .querySelectorAll(
      '[data-multi-upload]',
    )
    .forEach((wrapper) => {
      const input = wrapper.querySelector(
        '[data-multi-input]',
      );

      const preview = (
        wrapper.parentElement
          ?.querySelector(
            '[data-multi-preview]',
          )
      );

      if (
        !input
        || !preview
      ) {
        return;
      }

      input.addEventListener(
        'change',
        () => {
          clearMultiPreview(
            preview,
          );

          if (
            !validateImageInput(input)
          ) {
            input.value = '';
            return;
          }

          selectedFiles(input)
            .forEach((file) => {
              const image = (
                document.createElement(
                  'img',
                )
              );

              image.alt = (
                `Prévia de ${file.name}`
              );

              image.dataset.previewUrl = (
                URL.createObjectURL(file)
              );

              image.src = (
                image.dataset.previewUrl
              );

              preview.appendChild(image);
            });
        },
      );
    });

  const form = (
    document.querySelector(
      '[data-wizard-form]',
    )
  );

  if (!form) return;

  const total = Number(
    form.dataset.wizardTotal
    || 1,
  );

  const steps = [
    ...form.querySelectorAll(
      '[data-wizard-step]',
    ),
  ];

  const navItems = [
    ...document.querySelectorAll(
      '[data-step-nav]',
    ),
  ];

  const previous = form.querySelector(
    '[data-wizard-prev]',
  );

  const next = form.querySelector(
    '[data-wizard-next]',
  );

  const submit = form.querySelector(
    '[data-wizard-submit]',
  );

  const progress = (
    document.querySelector(
      '[data-wizard-progress]',
    )
  );

  const progressLabel = (
    document.querySelector(
      '[data-wizard-progress-label]',
    )
  );

  let current = 1;

  const focusFirst = (step) => {
    const first = step.querySelector(
      (
        'input:not([type="hidden"])'
        + ':not(.platform-file-input), '
        + 'select, textarea, button'
      ),
    );

    if (
      first
      && window
        .matchMedia(
          '(min-width: 761px)',
        )
        .matches
    ) {
      window.requestAnimationFrame(
        () => {
          first.focus({
            preventScroll: true,
          });
        },
      );
    }
  };

  const render = () => {
    steps.forEach((step) => {
      const active = (
        Number(
          step.dataset.wizardStep,
        )
        === current
      );

      step.hidden = !active;

      step.classList.toggle(
        'is-active',
        active,
      );

      if (active) {
        focusFirst(step);
      }
    });

    navItems.forEach((item) => {
      const index = Number(
        item.dataset.stepNav,
      );

      item.classList.toggle(
        'is-active',
        index === current,
      );

      item.classList.toggle(
        'is-complete',
        index < current,
      );
    });

    const percentage = Math.round(
      (current / total) * 100,
    );

    if (progress) {
      progress.style.width = (
        `${percentage}%`
      );
    }

    if (progressLabel) {
      progressLabel.textContent = (
        `${percentage}%`
      );
    }

    if (previous) {
      previous.hidden = (
        current === 1
      );
    }

    if (next) {
      next.hidden = (
        current === total
      );
    }

    if (submit) {
      submit.hidden = (
        current !== total
      );
    }

    const activeStep = steps.find(
      (step) => (
        Number(
          step.dataset.wizardStep,
        )
        === current
      ),
    );

    activeStep?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
    });
  };

  const validateStep = () => {
    const activeStep = steps.find(
      (step) => (
        Number(
          step.dataset.wizardStep,
        )
        === current
      ),
    );

    if (!activeStep) return true;

    const required = [
      ...activeStep.querySelectorAll(
        '[required]',
      ),
    ];

    for (const field of required) {
      if (!field.checkValidity()) {
        field.reportValidity();
        return false;
      }
    }

    const imageInputs = (
      activeStep.querySelectorAll(
        (
          '[data-image-input], '
          + '[data-multi-input]'
        ),
      )
    );

    for (
      const input
      of imageInputs
    ) {
      if (
        !validateImageInput(
          input,
          true,
        )
      ) {
        return false;
      }
    }

    return true;
  };

  next?.addEventListener(
    'click',
    () => {
      if (!validateStep()) return;

      if (current < total) {
        current += 1;
        render();
      }
    },
  );

  previous?.addEventListener(
    'click',
    () => {
      if (current > 1) {
        current -= 1;
        render();
      }
    },
  );

  navItems.forEach((item) => {
    item.addEventListener(
      'click',
      () => {
        const target = Number(
          item.dataset.stepNav,
        );

        if (target <= current) {
          current = target;
          render();
        }
      },
    );
  });

  const setSubmitLabel = (
    label,
  ) => {
    if (!submit) return;

    if (
      submit
      instanceof HTMLInputElement
    ) {
      submit.value = label;
    } else {
      submit.textContent = label;
    }
  };

  const submitLabel = (
    submit
    instanceof HTMLInputElement
  )
    ? submit.value
    : submit?.textContent;

  const resetSubmittingState = () => {
    form.dataset.submitting = 'false';

    form.classList.remove(
      'is-submitting',
    );

    form.removeAttribute(
      'aria-busy',
    );

    [
      previous,
      next,
      submit,
    ].forEach((control) => {
      if (control) {
        control.disabled = false;
      }
    });

    if (submitLabel) {
      setSubmitLabel(
        submitLabel,
      );
    }
  };

  form.addEventListener(
    'submit',
    (event) => {
      if (
        form.dataset.submitting
        === 'true'
      ) {
        event.preventDefault();
        return;
      }

      const imageInputs = (
        form.querySelectorAll(
          (
            '[data-image-input], '
            + '[data-multi-input]'
          ),
        )
      );

      for (
        const input
        of imageInputs
      ) {
        if (
          validateImageInput(input)
        ) {
          continue;
        }

        event.preventDefault();

        const errorStep = input.closest(
          '[data-wizard-step]',
        );

        if (errorStep) {
          current = (
            Number(
              errorStep
                .dataset
                .wizardStep,
            )
            || current
          );

          render();

          validateImageInput(
            input,
            true,
          );
        }

        return;
      }

      form.dataset.submitting = 'true';

      form.classList.add(
        'is-submitting',
      );

      form.setAttribute(
        'aria-busy',
        'true',
      );

      [
        previous,
        next,
        submit,
      ].forEach((control) => {
        if (control) {
          control.disabled = true;
        }
      });

      setSubmitLabel(
        'Publicando…',
      );
    },
  );

  window.addEventListener(
    'pageshow',
    (event) => {
      if (event.persisted) {
        resetSubmittingState();
      }
    },
  );

  const hasServerErrors = (
    form.querySelector(
      (
        '.field-errors, '
        + '.form-error, '
        + '[aria-invalid="true"]'
      ),
    )
  );

  if (hasServerErrors) {
    const errorStep = (
      hasServerErrors.closest(
        '[data-wizard-step]',
      )
    );

    if (errorStep) {
      current = (
        Number(
          errorStep
            .dataset
            .wizardStep,
        )
        || 1
      );
    }
  }

  resetSubmittingState();
  render();
})();