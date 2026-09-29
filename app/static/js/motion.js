(() => {
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const reducedMotion = motionPreference.matches;
  const header = document.querySelector('[data-site-header]');

  const updateHeader = () => {
    if (!header) return;
    header.classList.toggle('is-scrolled', window.scrollY > 18);
  };

  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  const revealTargets = document.querySelectorAll('[data-reveal], [data-reveal-stagger]');
  const hasIntersectionObserver = 'IntersectionObserver' in window;
  const formatter = new Intl.NumberFormat('pt-BR');
  const startedCounters = new WeakSet();

  const animateCounter = (counter) => {
    if (startedCounters.has(counter)) return;

    const rawValue = counter.dataset.countTo;
    if (!/^\d+$/.test(rawValue || '')) return;

    const target = Number(rawValue);
    if (!Number.isSafeInteger(target)) return;

    startedCounters.add(counter);

    const showFinalValue = () => {
      counter.textContent = formatter.format(target);
    };

    if (motionPreference.matches || !hasIntersectionObserver || target === 0) {
      showFinalValue();
      return;
    }

    counter.textContent = '0';
    let startedAt = null;
    const duration = 850;

    const updateCounter = (timestamp) => {
      if (motionPreference.matches) {
        showFinalValue();
        return;
      }

      if (startedAt === null) startedAt = timestamp;
      const progress = Math.min((timestamp - startedAt) / duration, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      counter.textContent = formatter.format(Math.floor(target * easedProgress));

      if (progress < 1) {
        window.requestAnimationFrame(updateCounter);
      } else {
        showFinalValue();
      }
    };

    window.requestAnimationFrame(updateCounter);
  };

  const revealElement = (element) => {
    element.classList.add('is-visible');
    if (element.matches('[data-count-to]')) animateCounter(element);
    element.querySelectorAll('[data-count-to]').forEach(animateCounter);
  };

  if (reducedMotion || !hasIntersectionObserver) {
    revealTargets.forEach(revealElement);
  } else {
    const observer = new IntersectionObserver((entries, instance) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        revealElement(entry.target);
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