document.addEventListener("DOMContentLoaded", () => {
  const closeInfoTips = (except = null) => {
    document.querySelectorAll("[data-info-trigger].is-open").forEach((button) => {
      if (button !== except) {
        button.classList.remove("is-open");
        button.setAttribute("aria-expanded", "false");
      }
    });
  };

  document.querySelectorAll("[data-info-trigger]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const shouldOpen = !button.classList.contains("is-open");
      closeInfoTips(button);
      button.classList.toggle("is-open", shouldOpen);
      button.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
    });
  });
  document.addEventListener("click", () => closeInfoTips());
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeInfoTips();
  });

  document.querySelectorAll("[data-image-upload]").forEach((root) => {
    const input = root.querySelector("[data-image-input]");
    const preview = root.querySelector("[data-image-preview]");
    const cropEditor = root.querySelector("[data-crop-editor]");
    const cropImage = cropEditor?.querySelector("[data-crop-image]");
    const cropStage = cropEditor?.querySelector("[data-crop-stage]");
    const cropTarget = cropEditor?.querySelector("[data-crop-target]");
    const cropOutput = cropEditor?.querySelector("[data-crop-output]");
    const cropReset = cropEditor?.querySelector("[data-crop-reset]");
    const cropX = cropEditor?.dataset.cropXId
      ? document.getElementById(cropEditor.dataset.cropXId)
      : null;
    const cropY = cropEditor?.dataset.cropYId
      ? document.getElementById(cropEditor.dataset.cropYId)
      : null;
    let objectUrl = null;

    const clamp = (value) => Math.max(0, Math.min(100, value));

    const updateCrop = (x, y) => {
      if (!cropImage || !cropX || !cropY) return;
      const safeX = Math.round(clamp(x));
      const safeY = Math.round(clamp(y));
      cropX.value = String(safeX);
      cropY.value = String(safeY);
      cropImage.style.objectPosition = `${safeX}% ${safeY}%`;
      if (cropTarget) {
        cropTarget.style.left = `${safeX}%`;
        cropTarget.style.top = `${safeY}%`;
      }
      if (cropOutput) cropOutput.value = `${safeX}% · ${safeY}%`;
    };

    const updateCropFromPointer = (event) => {
      if (!cropStage || !cropImage?.src) return;
      const rect = cropStage.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      updateCrop(
        ((event.clientX - rect.left) / rect.width) * 100,
        ((event.clientY - rect.top) / rect.height) * 100,
      );
    };

    if (cropStage) {
      cropStage.addEventListener("pointerdown", (event) => {
        if (!cropImage?.src) return;
        cropStage.setPointerCapture?.(event.pointerId);
        updateCropFromPointer(event);
      });
      cropStage.addEventListener("pointermove", (event) => {
        if (!cropStage.hasPointerCapture?.(event.pointerId)) return;
        updateCropFromPointer(event);
      });
      cropStage.addEventListener("pointerup", (event) => {
        cropStage.releasePointerCapture?.(event.pointerId);
      });
      cropStage.addEventListener("keydown", (event) => {
        if (!cropX || !cropY) return;
        const step = event.shiftKey ? 10 : 2;
        let x = Number(cropX.value || 50);
        let y = Number(cropY.value || 50);
        if (event.key === "ArrowLeft") x -= step;
        else if (event.key === "ArrowRight") x += step;
        else if (event.key === "ArrowUp") y -= step;
        else if (event.key === "ArrowDown") y += step;
        else return;
        event.preventDefault();
        updateCrop(x, y);
      });
      cropStage.tabIndex = 0;
    }

    cropReset?.addEventListener("click", () => updateCrop(50, 50));

    if (cropX && cropY) {
      updateCrop(Number(cropX.value || 50), Number(cropY.value || 50));
    }

    if (!input || !preview) return;
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(file);
      preview.style.backgroundImage = `url("${objectUrl}")`;
      preview.classList.add("has-image");
      if (cropImage && cropEditor) {
        cropImage.src = objectUrl;
        cropEditor.classList.add("has-image");
        updateCrop(50, 50);
      }
    });
  });

  document.querySelectorAll("[data-number-stepper]").forEach((root) => {
    const input = root.querySelector("input[type='number']");
    if (!input) return;
    root.querySelectorAll("[data-step]").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.step === "up") input.stepUp();
        else input.stepDown();
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.focus({ preventScroll: true });
      });
    });
  });

  const slugify = (value) => value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 190);

  document.querySelectorAll("[data-handle-field]").forEach((root) => {
    const input = root.querySelector("input");
    const status = root.querySelector("[data-handle-status]");
    const form = root.closest("form");
    const source = form?.querySelector("#display_name") || form?.querySelector("#name");
    if (!input || !status) return;
    let manuallyEdited = Boolean(input.value.trim());
    let timer;

    const check = () => {
      const normalized = slugify(input.value);
      input.value = normalized;
      if (!normalized) {
        status.textContent = "O IDDUN vai gerar este endereço automaticamente.";
        status.className = "admin-handle-status";
        return;
      }
      const params = new URLSearchParams({
        type: root.dataset.handleType,
        value: normalized,
      });
      if (root.dataset.currentId) params.set("current_id", root.dataset.currentId);
      status.textContent = "Verificando disponibilidade…";
      status.className = "admin-handle-status is-checking";
      fetch(`/admin/identificador/disponibilidade?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => response.json())
        .then((data) => {
          status.textContent = data.available ? `✓ iddun.com/${data.handle} está disponível` : data.message;
          status.className = `admin-handle-status ${data.available ? "is-available" : "is-unavailable"}`;
        })
        .catch(() => {
          status.textContent = "Não foi possível verificar agora. O servidor valida ao salvar.";
          status.className = "admin-handle-status";
        });
    };

    input.addEventListener("input", () => {
      manuallyEdited = true;
      clearTimeout(timer);
      timer = setTimeout(check, 300);
    });
    input.addEventListener("blur", check);

    source?.addEventListener("input", () => {
      if (!manuallyEdited || !input.value.trim()) {
        input.value = slugify(source.value);
        clearTimeout(timer);
        timer = setTimeout(check, 350);
      }
    });

    if (input.value) check();
  });
});
