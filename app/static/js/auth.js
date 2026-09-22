(() => {
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // Mantém texto, type e atributos acessíveis sincronizados.
  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;

    button.setAttribute('aria-pressed', 'false');

    button.addEventListener('click', () => {
      const willShow = input.type === 'password';
      const label = button.querySelector('[data-password-toggle-label]');
      input.type = willShow ? 'text' : 'password';

      if (label) {
        label.textContent = willShow ? 'Ocultar' : 'Mostrar';
      } else {
        // Compatibilidade com os controles de senha do cadastro.
        button.textContent = willShow ? 'Ocultar' : 'Mostrar';
      }

      button.setAttribute('aria-label', willShow ? 'Ocultar senha' : 'Mostrar senha');
      button.setAttribute('aria-pressed', String(willShow));
    });
  });

  const form = document.querySelector('[data-auth-form]');
  if (form) {
    const inputs = [...form.querySelectorAll('[data-validate]')];
    const submitButton = form.querySelector('[data-submit]');

    const validationMessage = (input) => {
      const value = input.value.trim();

      if (!value) {
        return input.dataset.validate === 'email'
          ? 'Informe seu e-mail.'
          : 'Informe sua senha.';
      }

      if (input.dataset.validate === 'email' && !emailPattern.test(value)) {
        return 'Digite um e-mail válido, como nome@exemplo.com.';
      }

      return '';
    };

    const renderValidation = (input) => {
      const field = input.closest('[data-field]');
      const output = document.getElementById(`${input.id}-client-error`);
      const message = validationMessage(input);

      field?.classList.toggle('has-error', Boolean(message));
      input.setAttribute('aria-invalid', String(Boolean(message)));
      if (output) output.textContent = message;
      return !message;
    };

    inputs.forEach((input) => {
      input.addEventListener('blur', () => {
        input.dataset.touched = 'true';
        renderValidation(input);
      });

      input.addEventListener('input', () => {
        if (input.dataset.touched === 'true' || input.getAttribute('aria-invalid') === 'true') {
          renderValidation(input);
        }
      });
    });

    form.addEventListener('submit', (event) => {
      if (submitButton?.dataset.submitting === 'true') {
        event.preventDefault();
        return;
      }

      const validity = inputs.map((input) => {
        input.dataset.touched = 'true';
        return renderValidation(input);
      });

      if (validity.includes(false)) {
        event.preventDefault();
        inputs.find((input) => input.getAttribute('aria-invalid') === 'true')?.focus();
        return;
      }

      if (submitButton) {
        submitButton.dataset.submitting = 'true';
        submitButton.classList.add('is-loading');
        submitButton.disabled = true;
        submitButton.setAttribute('aria-busy', 'true');
        submitButton.querySelector('.auth-submit__loading')?.setAttribute('aria-hidden', 'false');
      }
    });

    // Ao voltar pelo histórico do navegador, remove o loading preservado pelo
    // bfcache para que o usuário possa tentar novamente.
    window.addEventListener('pageshow', () => {
      if (!submitButton) return;
      submitButton.dataset.submitting = 'false';
      submitButton.classList.remove('is-loading');
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
      submitButton.querySelector('.auth-submit__loading')?.setAttribute('aria-hidden', 'true');
    });
  }

  // Os provedores dependem de OAuth e recuperação no backend. Enquanto essas
  // integrações não estão configuradas, o controle informa o estado sem levar
  // o usuário a uma rota quebrada ou simular um login inexistente.
  const integrationNote = document.getElementById('auth-integration-note');
  document.querySelectorAll('[data-auth-unavailable]').forEach((control) => {
    control.addEventListener('click', (event) => {
      event.preventDefault();
      if (integrationNote) integrationNote.textContent = control.dataset.authUnavailable;
    });
  });

  // Erros de credenciais vindos do servidor são anunciados e recebem foco,
  // sem depender apenas da cor para comunicar o problema.
  document.querySelector('[data-auth-general-error]')?.focus({ preventScroll: true });
})();
