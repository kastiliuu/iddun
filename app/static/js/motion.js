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
    // Revela quando 12% do bloco aparece. Um bloco alto (a grade do
    // Explorar no celular) nunca mostra 12% de si de uma vez, então ele é
    // revelado assim que entra, sem esperar um limiar inalcançável.
    // O que já está na tela ao carregar continua aparecendo de imediato.
    const revealRatio = 0.12;
    const tallShareOfScreen = 0.5;
    const measured = new WeakSet();
    const observer = new IntersectionObserver((entries, instance) => {
      entries.forEach((entry) => {
        const firstMeasure = !measured.has(entry.target);
        measured.add(entry.target);
        if (!entry.isIntersecting) return;
        const screenHeight = entry.rootBounds ? entry.rootBounds.height : window.innerHeight;
        const isTall = entry.boundingClientRect.height * revealRatio > screenHeight * tallShareOfScreen;
        if (!firstMeasure && entry.intersectionRatio < revealRatio && !isTall) return;
        revealElement(entry.target);
        instance.unobserve(entry.target);
      });
    }, { threshold: [0, revealRatio], rootMargin: '0px 0px -6% 0px' });

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