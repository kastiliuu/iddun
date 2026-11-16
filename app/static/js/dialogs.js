/*
 * Janelas sob demanda (ID-SOC-R1-06). Sem JavaScript, os links
 * [data-dialog-open] recarregam a página com a janela já aberta pelo
 * servidor; aqui ela abre no lugar, como modal, e devolve o foco a quem
 * abriu. Nada é enviado por este arquivo: os formulários são os da página.
 */
(() => {
  const dialogs = document.querySelectorAll('dialog[data-dialog]');
  if (!dialogs.length || typeof HTMLDialogElement === 'undefined') return;

  let opener = null;

  const open = (dialog, trigger) => {
    document.querySelectorAll('dialog[data-dialog][open]').forEach((other) => {
      if (other !== dialog) other.close();
    });
    opener = trigger || opener;
    if (dialog.open) dialog.close();
    dialog.showModal();
    const first = dialog.querySelector('[aria-invalid="true"], input:not([type="hidden"]), button, a');
    first?.focus();
  };

  // Aberta pelo servidor (?equipe=... ou erro de validação): vira modal.
  dialogs.forEach((dialog) => {
    if (dialog.open) {
      dialog.close();
      open(dialog, null);
    }
    dialog.addEventListener('close', () => {
      opener?.focus();
    });
    // Clique fora do conteúdo fecha, como o Esc.
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-dialog-open]');
    if (trigger) {
      const dialog = document.getElementById(trigger.dataset.dialogOpen);
      if (dialog) {
        event.preventDefault();
        open(dialog, trigger.closest('dialog') ? opener : trigger);
      }
      return;
    }
    const closer = event.target.closest('[data-dialog-close]');
    const dialog = closer?.closest('dialog');
    if (dialog) {
      event.preventDefault();
      dialog.close();
    }
  });
})();
