/* NEXO UNDAC V9.2 - navegación accesible. Sin dependencias ni telemetría. */
(function () {
  'use strict';
  const toggle = document.querySelector('[data-sidebar-toggle]');
  const sidebar = document.querySelector('#nexo-v92-sidebar');
  if (!toggle || !sidebar) return;
  const close = () => {
    document.body.classList.remove('nexo-v92-sidebar-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Abrir menú principal');
  };
  const open = () => {
    document.body.classList.add('nexo-v92-sidebar-open');
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-label', 'Cerrar menú principal');
  };
  toggle.addEventListener('click', () => document.body.classList.contains('nexo-v92-sidebar-open') ? close() : open());
  sidebar.addEventListener('click', (e) => {if (e.target.closest('a')) close();});
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
  document.addEventListener('click', (e) => {
    if (document.body.classList.contains('nexo-v92-sidebar-open') && !sidebar.contains(e.target) && !toggle.contains(e.target)) close();
  });
  const desktop = window.matchMedia('(min-width: 901px)');
  if (desktop.addEventListener) desktop.addEventListener('change', (e) => { if (e.matches) close(); });
})();
