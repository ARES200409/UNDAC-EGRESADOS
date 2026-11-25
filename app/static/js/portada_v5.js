/* NEXO UNDAC · Carrusel institucional V7
 * Avance automático cada 5,5 segundos incluso con el cursor encima.
 * Permite pausar o reanudar voluntariamente; respeta movimiento reducido.
 */
(() => {
  'use strict';

  function iniciarCarrusel() {
    const root = document.querySelector('[data-nexo-carousel]');
    if (!root || root.dataset.nexoInitialized === 'true') return;

    const slides = Array.from(root.querySelectorAll('.nexo-carousel-slide'));
    if (slides.length < 2) return;

    root.dataset.nexoInitialized = 'true';
    const dots = Array.from(root.querySelectorAll('[data-nexo-dot]'));
    const counter = root.querySelector('[data-nexo-count]');
    const caption = root.querySelector('[data-nexo-caption]');
    const buttons = root.querySelector('.nexo-carousel-buttons');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const intervalMs = 5500;

    let active = Math.max(0, slides.findIndex(slide => slide.classList.contains('is-active')));
    let paused = reduceMotion.matches;
    let timer = null;

    function show(index) {
      active = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => {
        const selected = i === active;
        slide.classList.toggle('is-active', selected);
        slide.setAttribute('aria-hidden', String(!selected));
      });
      dots.forEach((dot, i) => {
        const selected = i === active;
        dot.classList.toggle('is-active', selected);
        if (selected) dot.setAttribute('aria-current', 'true');
        else dot.removeAttribute('aria-current');
      });
      if (counter) {
        counter.textContent = `${String(active + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}`;
      }
      const figcaption = slides[active].querySelector('figcaption');
      if (caption && figcaption) caption.textContent = figcaption.textContent || '';
    }

    function stop() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function play() {
      stop();
      if (paused || document.hidden) return;
      timer = window.setInterval(() => show(active + 1), intervalMs);
    }

    let pauseButton = null;
    function updatePauseButton() {
      if (!pauseButton) return;
      pauseButton.innerHTML = paused
        ? '<i class="bi bi-play-fill" aria-hidden="true"></i>'
        : '<i class="bi bi-pause-fill" aria-hidden="true"></i>';
      pauseButton.setAttribute('aria-label', paused ? 'Reanudar carrusel' : 'Pausar carrusel');
      pauseButton.setAttribute('aria-pressed', String(paused));
      pauseButton.title = paused ? 'Reanudar fotografías' : 'Pausar fotografías';
    }

    if (buttons) {
      pauseButton = document.createElement('button');
      pauseButton.type = 'button';
      updatePauseButton();
      buttons.appendChild(pauseButton);
      pauseButton.addEventListener('click', () => {
        paused = !paused;
        updatePauseButton();
        play();
      });
    }

    root.querySelector('[data-nexo-prev]')?.addEventListener('click', () => {
      show(active - 1);
      play();
    });
    root.querySelector('[data-nexo-next]')?.addEventListener('click', () => {
      show(active + 1);
      play();
    });
    dots.forEach((dot, i) => {
      dot.addEventListener('click', () => {
        show(i);
        play();
      });
    });

    // No detenemos el carrusel al pasar el mouse o enfocar sus controles.
    // Se detiene al ocultarse la pestaña para evitar trabajo innecesario.
    document.addEventListener('visibilitychange', play);
    reduceMotion.addEventListener?.('change', event => {
      if (event.matches) {
        paused = true;
        updatePauseButton();
        stop();
      }
    });

    show(active);
    play();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciarCarrusel, { once: true });
  } else {
    iniciarCarrusel();
  }
})();
