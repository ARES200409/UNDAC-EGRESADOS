/* NEXO UNDAC - solo tema claro y oscuro */
(() => {
  const key = 'nexo_undac_theme';
  const root = document.documentElement;
  const allowed = new Set(['light','dark']);
  const preference = () => { try { const p = localStorage.getItem(key); return allowed.has(p) ? p : 'light'; } catch (e) { return 'light'; } };
  function apply(p) {
    const effective = p;
    root.dataset.theme = effective;
    root.dataset.themePreference = p;
    root.style.colorScheme = effective;
    const icon = effective === 'dark' ? 'bi-sun' : 'bi-moon-stars';
    document.querySelectorAll('[data-theme-icon]').forEach(el => el.className = 'bi ' + icon);
    const label = p === 'dark' ? 'Oscuro' : 'Claro';
    document.querySelectorAll('[data-theme-label]').forEach(el => el.textContent = label);
    document.querySelectorAll('[data-theme-toggle]').forEach(el => el.title = `Tema actual: ${label}. Cambiar tema`);
    if (window.Chart && window.Chart.instances) {
      const contrast = effective === 'dark' ? '#b8d1d4' : '#647b82';
      const grid = effective === 'dark' ? '#34505a' : '#e3eceb';
      Object.values(window.Chart.instances).forEach(chart => {
        chart.options.color = contrast;
        if (chart.options.scales) {
          Object.values(chart.options.scales).forEach(axis => {
            axis.ticks = {...(axis.ticks || {}), color: contrast};
            axis.grid = {...(axis.grid || {}), color: grid};
          });
        }
        if (chart.data && chart.data.datasets && chart.config.type === 'doughnut') {
          chart.data.datasets.forEach(ds => ds.borderColor = effective === 'dark' ? '#1a303a' : '#fff');
        }
        chart.update('none');
      });
    }
    window.dispatchEvent(new CustomEvent('nexo:theme-changed', {detail: {theme: effective}}));
  }
  // Aplicación inmediata para reducir el destello del tema anterior.
  apply(preference());
  function cycle() {
    const p = preference();
    const next = p === 'light' ? 'dark' : 'light';
    try { localStorage.setItem(key,next); } catch (e) {}
    apply(next);
  }
  document.addEventListener('DOMContentLoaded', () => {
    apply(preference());
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => btn.addEventListener('click', cycle));
  });
})();