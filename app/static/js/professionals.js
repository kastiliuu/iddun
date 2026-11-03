(() => {
  // Seguir e favoritar perfis gravam na conta por graph.js (PR 2).

  document.querySelectorAll('[data-gallery-track]').forEach((track) => {
    const section = track.closest('.public-profile-section');
    const previous = section?.querySelector('[data-gallery-prev]');
    const next = section?.querySelector('[data-gallery-next]');
    const distance = () => {
      const item = track.querySelector('figure');
      return item ? item.getBoundingClientRect().width + 12 : track.clientWidth * .8;
    };
    previous?.addEventListener('click', () => track.scrollBy({ left: -distance(), behavior: 'smooth' }));
    next?.addEventListener('click', () => track.scrollBy({ left: distance(), behavior: 'smooth' }));
  });
})();
