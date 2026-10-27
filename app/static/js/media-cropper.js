(() => {
  const clamp = (value, min = 0, max = 100) => (
    Math.max(min, Math.min(max, value))
  );

  const numberOrCenter = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? clamp(parsed) : 50;
  };

  const numberOrOne = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? clamp(parsed, 1, 3) : 1;
  };

  // Only the formats the server accepts are previewed. SVG and anything
  // else never becomes a blob: URL here; the server rejects it on submit.
  const previewableType = (file) => (
    ['image/jpeg', 'image/png', 'image/webp'].includes(file?.type)
  );

  const distance = (a, b) => (
    Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)
  );

  const initializeCropper = (root) => {
    if (root.dataset.mediaCropperReady === 'true') return;

    const stage = root.querySelector('[data-crop-stage]');
    const image = root.querySelector('[data-crop-image]');
    const output = root.querySelector('[data-crop-output]');
    const reset = root.querySelector('[data-crop-reset]');
    const zoomInput = root.querySelector('[data-crop-zoom]');
    const zoomValue = root.querySelector('[data-crop-zoom-value]');

    const uploadControl = root.closest(
      '[data-media-control], [data-image-upload]',
    );
    const preview = uploadControl?.querySelector('[data-image-preview]');
    const launch = uploadControl?.querySelector('[data-crop-launch]');
    const confirm = root.querySelector('[data-crop-confirm]');
    const cancel = root.querySelector('[data-crop-cancel]');

    const inputId = root.dataset.cropInputId;
    const input = (
      (inputId && document.getElementById(inputId))
      || uploadControl?.querySelector('[data-image-input]')
    );

    const focusXId = root.dataset.focusXId || root.dataset.cropXId;
    const focusYId = root.dataset.focusYId || root.dataset.cropYId;
    const focusX = focusXId ? document.getElementById(focusXId) : null;
    const focusY = focusYId ? document.getElementById(focusYId) : null;

    if (!stage || !image || !focusX || !focusY) return;

    root.dataset.mediaCropperReady = 'true';

    let x = numberOrCenter(focusX.value);
    let y = numberOrCenter(focusY.value);
    let zoom = numberOrOne(zoomInput?.value);
    let objectUrl = null;
    let resultUrl = null;
    let trigger = null;
    let isNewSelection = false;
    let saved = { x, y, zoom };
    let previousImage = image.getAttribute('src') || '';
    let previousPreview = preview?.style.backgroundImage || '';
    const pointers = new Map();
    let dragState = null;
    let pinchState = null;

    const announce = (message = 'Enquadramento atualizado.') => {
      if (!output) return;
      output.value = message;
      output.textContent = message;
    };

    const applyTransform = ({ announceChange = false } = {}) => {
      focusX.value = String(Math.round(x));
      focusY.value = String(Math.round(y));

      image.style.objectPosition = `${x}% ${y}%`;
      image.style.transformOrigin = `${x}% ${y}%`;
      image.style.transform = `scale(${zoom})`;

      if (preview) {
        preview.style.backgroundPosition = `${x}% ${y}%`;
      }

      if (zoomInput) zoomInput.value = zoom.toFixed(2);
      if (zoomValue) zoomValue.textContent = `${Math.round(zoom * 100)}%`;

      stage.setAttribute(
        'aria-valuetext',
        `Enquadramento horizontal ${Math.round(x)}%, vertical ${Math.round(y)}%, zoom ${Math.round(zoom * 100)}%`,
      );

      if (announceChange) announce();
    };

    const setPosition = (nextX, nextY, shouldAnnounce = false) => {
      x = numberOrCenter(nextX);
      y = numberOrCenter(nextY);
      applyTransform({ announceChange: shouldAnnounce });
    };

    const setZoom = (nextZoom, shouldAnnounce = false) => {
      zoom = numberOrOne(nextZoom);
      applyTransform({ announceChange: shouldAnnounce });
    };

    const resetEditor = (shouldAnnounce = true) => {
      x = 50;
      y = 50;
      zoom = 1;
      applyTransform({ announceChange: shouldAnnounce });
    };

    const openEditor = (origin) => {
      trigger = origin || input;
      if (!isNewSelection) {
        saved = {
          x: numberOrCenter(focusX.value),
          y: numberOrCenter(focusY.value),
          zoom,
        };
      }
      root.hidden = false;
      root.classList.add('is-open');
      root.setAttribute('aria-hidden', 'false');
      document.body.classList.add('media-cropper-dialog-open');
      requestAnimationFrame(() => stage.focus({ preventScroll: true }));
    };

    const closeEditor = () => {
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('media-cropper-dialog-open');
      trigger?.focus?.({ preventScroll: true });
    };

    const targetAspect = () => {
      const explicit = Number(root.dataset.cropAspect);
      if (Number.isFinite(explicit) && explicit > 0) return explicit;
      const bounds = stage.getBoundingClientRect();
      return bounds.height > 0 ? bounds.width / bounds.height : 1;
    };

    const cropRect = () => {
      const naturalWidth = image.naturalWidth;
      const naturalHeight = image.naturalHeight;
      const aspect = targetAspect();

      if (!naturalWidth || !naturalHeight || !aspect) return null;

      const imageAspect = naturalWidth / naturalHeight;
      let baseWidth;
      let baseHeight;

      if (imageAspect >= aspect) {
        baseHeight = naturalHeight;
        baseWidth = baseHeight * aspect;
      } else {
        baseWidth = naturalWidth;
        baseHeight = baseWidth / aspect;
      }

      const width = baseWidth / zoom;
      const height = baseHeight / zoom;
      const centerX = (x / 100) * naturalWidth;
      const centerY = (y / 100) * naturalHeight;

      return {
        x: clamp(centerX - (width / 2), 0, naturalWidth - width),
        y: clamp(centerY - (height / 2), 0, naturalHeight - height),
        width,
        height,
        aspect,
      };
    };

    const replaceInputWithCrop = async () => {
      if (!input || !image.complete || !image.naturalWidth) return false;

      const rect = cropRect();
      if (!rect) return false;

      const kind = root.dataset.cropKind || 'image';
      const maxWidth = kind === 'avatar' ? 1024 : 1600;
      const outputWidth = Math.max(1, Math.min(maxWidth, Math.round(rect.width)));
      const outputHeight = Math.max(1, Math.round(outputWidth / rect.aspect));
      const canvas = document.createElement('canvas');
      canvas.width = outputWidth;
      canvas.height = outputHeight;
      const context = canvas.getContext('2d');

      if (!context) return false;

      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'high';
      context.drawImage(
        image,
        rect.x,
        rect.y,
        rect.width,
        rect.height,
        0,
        0,
        outputWidth,
        outputHeight,
      );

      const blob = await new Promise((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', 0.9);
      });

      if (!blob) return false;

      const originalName = input.files?.[0]?.name || `iddun-${kind}.jpg`;
      const baseName = originalName.replace(/\.[^.]+$/, '');
      const file = new File(
        [blob],
        `${baseName}-crop.jpg`,
        { type: 'image/jpeg', lastModified: Date.now() },
      );
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;

      if (resultUrl) URL.revokeObjectURL(resultUrl);
      resultUrl = URL.createObjectURL(blob);

      image.src = resultUrl;
      image.style.transform = 'scale(1)';
      image.style.transformOrigin = '50% 50%';
      image.style.objectPosition = '50% 50%';

      if (preview) {
        preview.style.backgroundImage = `url("${resultUrl}")`;
        preview.style.backgroundPosition = '50% 50%';
        preview.classList.add('has-image');
      }

      x = 50;
      y = 50;
      zoom = 1;
      focusX.value = '50';
      focusY.value = '50';
      applyTransform();
      return true;
    };

    launch?.addEventListener('click', () => openEditor(launch));

    confirm?.addEventListener('click', async () => {
      confirm.disabled = true;
      root.classList.add('is-processing');

      try {
        const cropped = await replaceInputWithCrop();
        if (!cropped) {
          applyTransform();
        }
        previousImage = image.getAttribute('src') || '';
        previousPreview = preview?.style.backgroundImage || '';
        isNewSelection = false;
        saved = { x, y, zoom };
        if (launch) launch.hidden = false;
        announce('Enquadramento aplicado.');
        closeEditor();
      } catch (error) {
        console.error('[IDDUN] Não foi possível gerar o recorte.', error);
        announce('Não foi possível gerar o recorte. Tente outra imagem.');
      } finally {
        root.classList.remove('is-processing');
        confirm.disabled = false;
      }
    });

    cancel?.addEventListener('click', () => {
      x = saved.x;
      y = saved.y;
      zoom = saved.zoom;
      applyTransform();

      if (isNewSelection && input?.files?.length) {
        input.value = '';
        image.src = previousImage;
        if (preview) preview.style.backgroundImage = previousPreview;
      }

      isNewSelection = false;
      closeEditor();
    });

    reset?.addEventListener('click', () => {
      resetEditor();
      stage.focus({ preventScroll: true });
    });

    zoomInput?.addEventListener('input', () => {
      setZoom(zoomInput.value);
    });
    zoomInput?.addEventListener('change', () => {
      setZoom(zoomInput.value, true);
    });

    stage.addEventListener('wheel', (event) => {
      if (!image.getAttribute('src')) return;
      event.preventDefault();
      const direction = event.deltaY > 0 ? -0.08 : 0.08;
      setZoom(zoom + direction);
    }, { passive: false });

    stage.addEventListener('pointerdown', (event) => {
      if (!image.getAttribute('src') || event.button > 0) return;

      pointers.set(event.pointerId, event);
      stage.setPointerCapture?.(event.pointerId);

      if (pointers.size === 1) {
        dragState = {
          pointerId: event.pointerId,
          clientX: event.clientX,
          clientY: event.clientY,
          x,
          y,
        };
        stage.classList.add('is-dragging');
      } else if (pointers.size === 2) {
        const [first, second] = [...pointers.values()];
        pinchState = {
          distance: distance(first, second),
          zoom,
        };
        dragState = null;
      }

      event.preventDefault();
    });

    stage.addEventListener('pointermove', (event) => {
      if (!pointers.has(event.pointerId)) return;
      pointers.set(event.pointerId, event);

      if (pointers.size >= 2 && pinchState) {
        const [first, second] = [...pointers.values()];
        const currentDistance = distance(first, second);
        if (pinchState.distance > 0) {
          setZoom(
            pinchState.zoom * (currentDistance / pinchState.distance),
          );
        }
        return;
      }

      if (!dragState || dragState.pointerId !== event.pointerId) return;

      const bounds = stage.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;

      const deltaX = ((event.clientX - dragState.clientX) / bounds.width) * 100;
      const deltaY = ((event.clientY - dragState.clientY) / bounds.height) * 100;

      setPosition(
        dragState.x - (deltaX / zoom),
        dragState.y - (deltaY / zoom),
      );
    });

    const releasePointer = (event) => {
      if (!pointers.has(event.pointerId)) return;

      pointers.delete(event.pointerId);
      if (stage.hasPointerCapture?.(event.pointerId)) {
        stage.releasePointerCapture(event.pointerId);
      }

      if (pointers.size < 2) pinchState = null;
      if (!pointers.size) {
        dragState = null;
        stage.classList.remove('is-dragging');
        applyTransform({ announceChange: true });
      }
    };

    stage.addEventListener('pointerup', releasePointer);
    stage.addEventListener('pointercancel', releasePointer);

    stage.addEventListener('keydown', (event) => {
      const step = event.shiftKey ? 8 : 2;
      let handled = true;

      if (event.key === 'ArrowLeft') setPosition(x - step, y);
      else if (event.key === 'ArrowRight') setPosition(x + step, y);
      else if (event.key === 'ArrowUp') setPosition(x, y - step);
      else if (event.key === 'ArrowDown') setPosition(x, y + step);
      else if (event.key === '+' || event.key === '=') setZoom(zoom + 0.1);
      else if (event.key === '-') setZoom(zoom - 0.1);
      else if (event.key === 'Home') resetEditor(false);
      else handled = false;

      if (handled) {
        event.preventDefault();
        applyTransform({ announceChange: true });
      }
    });

    root.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && root.classList.contains('is-open')) {
        event.preventDefault();
        cancel?.click();
      }
    });

    input?.addEventListener('change', () => {
      const file = input.files?.[0];
      if (!file || !previewableType(file)) return;

      if (objectUrl) URL.revokeObjectURL(objectUrl);

      saved = { x, y, zoom };
      previousImage = image.getAttribute('src') || '';
      previousPreview = preview?.style.backgroundImage || '';
      isNewSelection = true;
      objectUrl = URL.createObjectURL(file);
      image.src = objectUrl;

      root.classList.add('has-image');
      root.removeAttribute('hidden');
      resetEditor(false);
      openEditor(input);
    });

    image.addEventListener('load', () => {
      applyTransform();
    });

    window.addEventListener('pagehide', () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      if (resultUrl) URL.revokeObjectURL(resultUrl);
    }, { once: true });

    if (image.getAttribute('src')) {
      root.classList.add('has-image');
      root.removeAttribute('hidden');
    }

    if (!stage.hasAttribute('tabindex')) stage.tabIndex = 0;
    applyTransform();
  };

  const initializeAll = () => {
    document
      .querySelectorAll('[data-media-cropper], [data-crop-editor]')
      .forEach(initializeCropper);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAll, { once: true });
  } else {
    initializeAll();
  }
})();
