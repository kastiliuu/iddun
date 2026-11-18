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

  // data-once: um envio por vez (P-003, ações de serviço e horário). O
  // botão fica ocupado até a resposta do servidor trocar a página; o
  // estado exibido continua sendo o que o servidor confirmar.
  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.hasAttribute('data-once')) return;
    if (event.defaultPrevented) return;
    if (form.dataset.sending === 'true') {
      event.preventDefault();
      return;
    }
    form.dataset.sending = 'true';
    const button = event.submitter || form.querySelector('[type="submit"]');
    window.setTimeout(() => {
      button?.setAttribute('aria-busy', 'true');
      button?.setAttribute('disabled', '');
    }, 0);
  });

  // Voltar pelo histórico (bfcache) devolve o formulário utilizável.
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[data-once][data-sending="true"]').forEach((form) => {
      delete form.dataset.sending;
      form.querySelectorAll('[aria-busy="true"]').forEach((button) => {
        button.removeAttribute('aria-busy');
        button.removeAttribute('disabled');
      });
    });
  });
})();
