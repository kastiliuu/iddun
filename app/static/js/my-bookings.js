/*
 * Minhas reservas (UX-BOOKINGS-001). Cada reserva é um <details> nativo e
 * funciona sem este script. Aqui só:
 * - abre a reserva indicada pela âncora (#booking-title-ID, #reserva-ID,
 *   #detalhes-reserva-ID, #reserva-confirmada) ou por ?confirmada=ID;
 * - depois de um formulário (POST + redirect), reabre a mesma reserva,
 *   põe o foco nela e liga a mensagem do topo ao resumo;
 * - lembra quais reservas estavam abertas ao voltar pelo navegador.
 * O armazenamento é só conveniência: se falhar, nada quebra.
 */
(() => {
  'use strict';

  const list = document.querySelector('[data-my-bookings]');
  if (!list) return;

  const SUBMIT_KEY = 'iddun:my-bookings:after-submit';
  const OPEN_KEY = `iddun:my-bookings:open:${window.location.pathname}${window.location.search}`;

  const storage = {
    get(key) {
      try { return window.sessionStorage.getItem(key); } catch (error) { return null; }
    },
    set(key, value) {
      try { window.sessionStorage.setItem(key, value); } catch (error) { /* sem armazenamento */ }
    },
    remove(key) {
      try { window.sessionStorage.removeItem(key); } catch (error) { /* sem armazenamento */ }
    },
  };

  const detailsFor = (id) => (id ? list.querySelector(`details[data-booking-id="${CSS.escape(String(id))}"]`) : null);

  const detailsFromHash = () => {
    const hash = decodeURIComponent(window.location.hash.slice(1));
    if (!hash) return null;
    const target = document.getElementById(hash);
    if (!target || !list.contains(target)) return null;
    return target.matches('details') ? target : target.closest('li')?.querySelector('details');
  };

  const reveal = (details, { describedBy } = {}) => {
    if (!details) return;
    details.open = true;
    const summary = details.querySelector('summary');
    if (describedBy) summary.setAttribute('aria-describedby', describedBy);
    details.closest('li').scrollIntoView({ block: 'start' });
    summary.focus({ preventScroll: true });
  };

  const rememberOpen = () => {
    const open = [...list.querySelectorAll('details[open]')].map((item) => item.dataset.bookingId);
    storage.set(OPEN_KEY, JSON.stringify(open));
  };

  // 1. Voltar pelo navegador: reabre o que estava aberto.
  try {
    const open = JSON.parse(storage.get(OPEN_KEY) || '[]');
    if (Array.isArray(open)) open.forEach((id) => { const item = detailsFor(id); if (item) item.open = true; });
  } catch (error) { /* valor inválido: ignora */ }

  // 2. Depois de um formulário: a mesma reserva, com a mensagem do topo.
  const submitted = storage.get(SUBMIT_KEY);
  storage.remove(SUBMIT_KEY);
  const flash = document.querySelector('[data-flash-message]');
  if (flash && !flash.id) flash.id = 'mensagem-reservas';

  const confirmed = new URLSearchParams(window.location.search).get('confirmada');
  if (submitted && detailsFor(submitted)) {
    reveal(detailsFor(submitted), { describedBy: flash ? flash.id : undefined });
  } else if (detailsFromHash()) {
    reveal(detailsFromHash());
  } else if (confirmed && detailsFor(confirmed)) {
    reveal(detailsFor(confirmed));
  }

  list.addEventListener('toggle', rememberOpen, true);

  list.addEventListener('submit', (event) => {
    const details = event.target.closest('details[data-booking-id]');
    if (details) storage.set(SUBMIT_KEY, details.dataset.bookingId);
  });

  window.addEventListener('hashchange', () => reveal(detailsFromHash()));
})();
