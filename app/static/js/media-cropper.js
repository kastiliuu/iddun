(() => {
  const clamp = (value) => (
    Math.max(0, Math.min(100, value))
  );

  const numberOrCenter = (value) => {
    const parsed = Number(value);

    return Number.isFinite(parsed)
      ? clamp(parsed)
      : 50;
  };

  const initializeCropper = (root) => {
    if (
      root.dataset.mediaCropperReady
      === 'true'
    ) {
      return;
    }

    const stage = root.querySelector(
      '[data-crop-stage]',
    );
    const image = root.querySelector(
      '[data-crop-image]',
    );
    const target = root.querySelector(
      '[data-crop-target]',
    );
    const output = root.querySelector(
      '[data-crop-output]',
    );
    const reset = root.querySelector(
      '[data-crop-reset]',
    );

    const uploadControl = root.closest(
      (
        '[data-media-control], '
        + '[data-image-upload]'
      ),
    );

    const preview = uploadControl?.querySelector(
      '[data-image-preview]',
    );

    const inputId = (
      root.dataset.cropInputId
    );

    const input = (
      (
        inputId
        && document.getElementById(inputId)
      )
      || uploadControl?.querySelector(
        '[data-image-input]',
      )
    );

    const focusXId = (
      root.dataset.focusXId
      || root.dataset.cropXId
    );

    const focusYId = (
      root.dataset.focusYId
      || root.dataset.cropYId
    );

    const focusX = focusXId
      ? document.getElementById(focusXId)
      : null;

    const focusY = focusYId
      ? document.getElementById(focusYId)
      : null;

    if (
      !stage
      || !image
      || !focusX
      || !focusY
    ) {
      return;
    }

    root.dataset.mediaCropperReady = 'true';

    let x = numberOrCenter(focusX.value);
    let y = numberOrCenter(focusY.value);
    let objectUrl = null;
    let dragState = null;

    const announcePosition = () => {
      if (!output) return;

      const value = (
        `${Math.round(x)}% · `
        + `${Math.round(y)}%`
      );

      output.value = value;
      output.textContent = value;
    };

    const updatePosition = (
      nextX,
      nextY,
      announce = false,
    ) => {
      x = Math.round(
        numberOrCenter(nextX),
      );
      y = Math.round(
        numberOrCenter(nextY),
      );

      if (announce) {
        output?.setAttribute(
          'aria-live',
          'polite',
        );
      }

      focusX.value = String(x);
      focusY.value = String(y);

      image.style.objectPosition = (
        `${x}% ${y}%`
      );

      if (preview) {
        preview.style.backgroundPosition = (
          `${x}% ${y}%`
        );
      }

      if (target) {
        target.style.left = `${x}%`;
        target.style.top = `${y}%`;
      }

      stage.setAttribute(
        'aria-valuetext',
        (
          `Horizontal ${x}%, `
          + `vertical ${y}%`
        ),
      );

      announcePosition();
    };

    const releasePointer = (event) => {
      if (!dragState) return;

      if (
        stage.hasPointerCapture?.(
          event.pointerId,
        )
      ) {
        stage.releasePointerCapture(
          event.pointerId,
        );
      }

      dragState = null;

      stage.classList.remove(
        'is-dragging',
      );

      output?.setAttribute(
        'aria-live',
        'polite',
      );

      updatePosition(x, y, true);
    };

    stage.addEventListener(
      'pointerdown',
      (event) => {
        if (
          !image.getAttribute('src')
          || event.button > 0
        ) {
          return;
        }

        dragState = {
          pointerId: event.pointerId,
          clientX: event.clientX,
          clientY: event.clientY,
          x,
          y,
        };

        output?.setAttribute(
          'aria-live',
          'off',
        );

        stage.classList.add(
          'is-dragging',
        );

        stage.setPointerCapture?.(
          event.pointerId,
        );

        event.preventDefault();
      },
    );

    stage.addEventListener(
      'pointermove',
      (event) => {
        if (
          !dragState
          || dragState.pointerId
          !== event.pointerId
        ) {
          return;
        }

        const bounds = (
          stage.getBoundingClientRect()
        );

        if (
          !bounds.width
          || !bounds.height
        ) {
          return;
        }

        const deltaX = (
          (
            event.clientX
            - dragState.clientX
          )
          / bounds.width
        ) * 100;

        const deltaY = (
          (
            event.clientY
            - dragState.clientY
          )
          / bounds.height
        ) * 100;

        updatePosition(
          dragState.x - deltaX,
          dragState.y - deltaY,
        );
      },
    );

    stage.addEventListener(
      'pointerup',
      releasePointer,
    );

    stage.addEventListener(
      'pointercancel',
      releasePointer,
    );

    stage.addEventListener(
      'keydown',
      (event) => {
        const step = (
          event.shiftKey ? 10 : 2
        );

        let nextX = x;
        let nextY = y;

        if (event.key === 'ArrowLeft') {
          nextX -= step;
        } else if (
          event.key === 'ArrowRight'
        ) {
          nextX += step;
        } else if (
          event.key === 'ArrowUp'
        ) {
          nextY -= step;
        } else if (
          event.key === 'ArrowDown'
        ) {
          nextY += step;
        } else if (
          event.key === 'Home'
        ) {
          nextX = 50;
          nextY = 50;
        } else {
          return;
        }

        event.preventDefault();

        updatePosition(
          nextX,
          nextY,
          true,
        );
      },
    );

    reset?.addEventListener(
      'click',
      () => {
        updatePosition(
          50,
          50,
          true,
        );

        stage.focus({
          preventScroll: true,
        });
      },
    );

    input?.addEventListener(
      'change',
      () => {
        const file = input.files?.[0];

        if (!file) return;

        if (objectUrl) {
          URL.revokeObjectURL(
            objectUrl,
          );
        }

        objectUrl = (
          URL.createObjectURL(file)
        );

        image.src = objectUrl;

        root.classList.add(
          'has-image',
        );

        root.removeAttribute('hidden');

        updatePosition(
          50,
          50,
          true,
        );
      },
    );

    window.addEventListener(
      'pagehide',
      () => {
        if (objectUrl) {
          URL.revokeObjectURL(
            objectUrl,
          );
        }
      },
      {
        once: true,
      },
    );

    if (image.getAttribute('src')) {
      root.classList.add(
        'has-image',
      );

      root.removeAttribute('hidden');
    }

    if (
      !stage.hasAttribute('tabindex')
    ) {
      stage.tabIndex = 0;
    }

    updatePosition(x, y);
  };

  const initializeAll = () => {
    document
      .querySelectorAll(
        (
          '[data-media-cropper], '
          + '[data-crop-editor]'
        ),
      )
      .forEach(initializeCropper);
  };

  if (
    document.readyState === 'loading'
  ) {
    document.addEventListener(
      'DOMContentLoaded',
      initializeAll,
      {
        once: true,
      },
    );
  } else {
    initializeAll();
  }
})();