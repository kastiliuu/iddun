document.addEventListener("DOMContentLoaded", () => {
  const uploadRoot = document.querySelector("[data-client-image-upload]");
  const input = uploadRoot?.querySelector("[data-client-image-input]");
  const formPreview = uploadRoot?.querySelector("[data-client-image-preview]");
  const heroAvatar = document.querySelector("[data-account-hero-avatar]");
  const editButton = document.querySelector("[data-account-avatar-edit]");
  const progress = document.querySelector("[data-account-progress]");

  const updateAvatarPreviews = (file) => {
    if (!file) return;

    const objectUrl = URL.createObjectURL(file);

    if (formPreview) {
      formPreview.style.backgroundImage = `url("${objectUrl}")`;
      formPreview.classList.add("has-image");
    }

    if (heroAvatar) {
      heroAvatar.style.backgroundImage = `url("${objectUrl}")`;
      heroAvatar.classList.add("account-avatar--photo");
      heroAvatar.textContent = "";
    }
  };

  input?.addEventListener("change", () => {
    updateAvatarPreviews(input.files?.[0]);
  });

  // The camera affordance reuses the existing form input instead of creating
  // a second upload flow with different validation or backend behavior.
  editButton?.addEventListener("click", () => {
    input?.click();
  });

  if (progress) {
    const target = `${Number(progress.dataset.progress) || 0}%`;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion) {
      progress.style.width = target;
    } else {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          progress.style.width = target;
        });
      });
    }
  }
});
