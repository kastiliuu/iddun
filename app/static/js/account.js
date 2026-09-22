document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-client-image-upload]");
  if (!root) return;
  const input = root.querySelector("[data-client-image-input]");
  const preview = root.querySelector("[data-client-image-preview]");
  input?.addEventListener("change", () => {
    const file = input.files?.[0];
    if (!file || !preview) return;
    preview.style.backgroundImage = `url("${URL.createObjectURL(file)}")`;
    preview.classList.add("has-image");
  });
});
