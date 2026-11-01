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

  // Mesmo desenho do ícone 'alert-circle' de components/icon.html.
  const errorIcon = () => {
    const svgNs = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNs, 'svg');
    svg.setAttribute('class', 'icon ds-field-errors__icon');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    const circle = document.createElementNS(svgNs, 'circle');
    circle.setAttribute('cx', '12');
    circle.setAttribute('cy', '12');
    circle.setAttribute('r', '9');
    const mark = document.createElementNS(svgNs, 'path');
    mark.setAttribute('d', 'M12 7.5v5.5M12 16.5h.01');
    svg.append(circle, mark);
    return svg;
  };

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
    // V-02a: o mesmo componente de erro do servidor (macro field_errors).
    const errorList = (
      document.createElement('div')
    );
    const errorItem = (
      document.createElement('p')
    );
    const errorText = (
      document.createElement('span')
    );

    errorList.id = errorId;
    errorList.className = (
      'ds-field-errors '
      + 'platform-client-errors'
    );
    errorList.dataset.clientFileError = '';

    errorList.setAttribute(
      'role',
      'alert',
    );

    errorItem.className = 'ds-field-errors__item';
    errorText.textContent = message;
    errorItem.append(errorIcon(), errorText);
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

    const isPortfolio = (
      input.name
      === 'portfolio_files'
    );

    return {
      minimum: 0,
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

  // V-02a: depois de um erro do servidor, o foco vai para o primeiro campo
  // inválido.
  // Grupos de caixas (fieldset com erro) recebem o foco na primeira opção.
  const firstServerError = document.querySelector(
    'form [aria-invalid="true"], '
    + 'form fieldset[aria-describedby*="-errors"] input',
  );

  if (firstServerError) {
    firstServerError.scrollIntoView({ block: 'center' });
    firstServerError.focus({ preventScroll: true });
  }

  // V-03: ao voltar de uma remoção (#portfolio, #galeria), o foco vai
  // para a seção, para o leitor de tela anunciar onde a pessoa está.
  const hashTarget = (
    window.location.hash
    && document.getElementById(
      decodeURIComponent(window.location.hash.slice(1)),
    )
  );

  if (
    !firstServerError
    && hashTarget
    && hashTarget.matches('[data-focus-on-hash]')
  ) {
    hashTarget.focus({ preventScroll: true });
  }

  // NV-07: o bloco de horários aparece só quando o funcionamento é
  // "Horários fixos" (seleção no editor, cartões no cadastro por etapas).
  // Sem JavaScript ele continua visível.
  const hoursControls = [
    ...document.querySelectorAll(
      'select[name="business_hours_mode"], input[name="business_hours_mode"]',
    ),
  ];
  const hoursPanel = document.querySelector('[data-hours-panel]');

  if (hoursControls.length && hoursPanel) {
    const syncHoursPanel = () => {
      const value = hoursControls.find(
        (control) => control.tagName === 'SELECT' || control.checked,
      )?.value;
      hoursPanel.hidden = value !== 'fixed_hours';
    };

    hoursControls.forEach((control) => {
      control.addEventListener('change', syncHoursPanel);
    });
    syncHoursPanel();
  }

  // Onboarding por etapas (PR 2): só melhora o formulário comum.
  // Erro geral da etapa recebe o foco; contador da apresentação; o botão
  // mostra "Salvando…" e não aceita segundo clique.
  const onbAlert = document.querySelector('[data-onb-alert]');

  if (onbAlert && !firstServerError) {
    onbAlert.focus();
  }

  document
    .querySelectorAll('[data-onb-counter]')
    .forEach((field) => {
      const output = document.querySelector(
        `[data-onb-count="${field.dataset.onbCounter}"]`,
      );

      if (!output) return;

      const update = () => {
        const length = field.value.trim().length;
        output.textContent = `${length} de 2000 caracteres.`;
      };

      field.addEventListener('input', update);
      update();
    });

  document
    .querySelectorAll('[data-onb-submit]')
    .forEach((button) => {
      button.form?.addEventListener('submit', (event) => {
        if (button.disabled) return;
        window.setTimeout(() => {
          if (event.defaultPrevented) return;
          button.disabled = true;
          button.value = 'Salvando…';
        }, 0);
      });
    });
})();
