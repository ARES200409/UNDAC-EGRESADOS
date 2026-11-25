/* NEXO UNDAC V10.7: mejoras progresivas; no guarda datos por fuera del backend. */
(() => {
  const init = () => {
    const main = document.querySelector('main.nexo-egresado-v107');
    if (!main) return;
    main.querySelectorAll('[data-nexo-primary-form]').forEach(form => {
      const counter = form.querySelector('[data-nexo-progress-count]');
      if (counter) {
        // Los radio se contabilizan como un campo (por nombre), no como varias entradas.
        const required = Array.from(form.querySelectorAll('[required]')).filter(el => el.type !== 'hidden');
        const groups = new Map();
        required.forEach((el,index) => {
          const key = (el.type === 'radio' || el.type === 'checkbox') ? `group:${el.name||index}` : `field:${index}`;
          if (!groups.has(key)) groups.set(key,[]);
          groups.get(key).push(el);
        });
        const update = () => {
          let completed=0;
          for (const els of groups.values()) {
            if (els.some(el=>el.disabled || el.closest('[hidden]'))) {completed++;continue;}
            const el=els[0];
            const checked=els.some(x=>x.checked);
            if (el.type === 'radio' || el.type === 'checkbox' ? checked : el.value.trim() !== '' && el.checkValidity()) completed++;
          }
          counter.textContent=groups.size?`${completed} de ${groups.size} campos obligatorios`:'Campos opcionales';
        };
        form.addEventListener('input', update);
        form.addEventListener('change', update);
        update();
      }
      form.addEventListener('submit', () => {
        // Envío HTML estándar y protección contra dobles clics; la página del servidor confirma el resultado.
        if (!form.checkValidity()) return;
        const button = form.querySelector('button[type="submit"]');
        if (button && !button.dataset.nexoSubmitting) {
          button.dataset.nexoSubmitting='1';
          button.setAttribute('aria-busy','true');
          const original = button.textContent.trim();
          if (original) button.setAttribute('data-nexo-original-label',original);
          const txt=button.querySelector('[data-nexo-button-text]');
          if (txt) txt.textContent='Enviando…';
        }
      });
    });
  };
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
