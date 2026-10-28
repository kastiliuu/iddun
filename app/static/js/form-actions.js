(() => {
  'use strict';

  // Keep form behaviour in external, same-origin scripts under strict CSP.
  document.addEventListener('change', (event) => {
    const control = event.target;
    if (!(control instanceof HTMLSelectElement)
        || !control.matches('select[data-auto-submit="true"]')) return;
    // Match the previous inline this.form.submit() semantics.
    control.form?.submit();
  });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)
        || !form.hasAttribute('data-confirm-submit')) return;
    const message = form.getAttribute('data-confirm-submit');
    if (!window.confirm(message || 'Confirmar esta ação?')) {
      event.preventDefault();
    }
  });
})();
