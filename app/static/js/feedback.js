document.addEventListener('DOMContentLoaded', () => {
  const messages = document.querySelectorAll('[data-flash-message]');

  const dismiss = (message) => {
    if (!message || message.dataset.closing === 'true') return;

    message.dataset.closing = 'true';
    message.classList.add('is-leaving');

    window.setTimeout(() => {
      message.remove();
    }, 280);
  };

  messages.forEach((message, index) => {
    const closeButton = message.querySelector('[data-flash-close]');
    closeButton?.addEventListener('click', () => dismiss(message));

    window.setTimeout(() => {
      dismiss(message);
    }, 3500 + (index * 250));
  });
});
