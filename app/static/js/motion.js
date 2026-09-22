(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const header = document.querySelector('[data-site-header]');

  const updateHeader = () => {
    if (!header) return;
    header.classList.toggle('is-scrolled', window.scrollY > 18);
  };

  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  const revealTargets = document.querySelectorAll('[data-reveal], [data-reveal-stagger]');

  if (reducedMotion || !('IntersectionObserver' in window)) {
    revealTargets.forEach((el) => el.classList.add('is-visible'));
  } else {
    const observer = new IntersectionObserver((entries, instance) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        instance.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

    revealTargets.forEach((el) => observer.observe(el));
  }

  if (!reducedMotion) {
    const parallaxMedia = document.querySelector('[data-parallax-media]');
    const parallaxRoot = document.querySelector('[data-parallax-root]');

    if (parallaxMedia && parallaxRoot) {
      let ticking = false;
      const updateParallax = () => {
        const rect = parallaxRoot.getBoundingClientRect();
        const viewport = window.innerHeight || 1;
        const progress = Math.max(-1, Math.min(1, (viewport - rect.top) / (viewport + rect.height)));
        parallaxMedia.style.setProperty('--parallax-y', `${(progress * 14).toFixed(2)}px`);
        parallaxMedia.style.setProperty('--parallax-scale', (1.025 + progress * .012).toFixed(4));
        ticking = false;
      };

      const requestParallax = () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(updateParallax);
      };

      updateParallax();
      window.addEventListener('scroll', requestParallax, { passive: true });
      window.addEventListener('resize', requestParallax, { passive: true });
    }
  }
})();
