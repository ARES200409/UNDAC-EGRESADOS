/* NEXO UNDAC V11.5: interacción real, historial optativo local y guías estructuradas.
   Las preguntas solo se envían al mismo backend Flask que ya tenía el proyecto. */
(() => {
  'use strict';
  const root = document.getElementById('nexo-chat');
  if (!root) return;
  const $ = id => root.querySelector('#' + id);
  const ui = {
    open: $('nexo-chat-open'), panel: $('nexo-chat-panel'), close: $('nexo-chat-close'),
    new: $('nexo-chat-new'), historyButton: $('nexo-chat-history-toggle'),
    history: $('nexo-chat-history'), historyClose: $('nexo-chat-history-close'),
    historyList: $('nexo-chat-history-list'), save: $('nexo-chat-save'),
    clear: $('nexo-chat-clear'), export: $('nexo-chat-export'),
    expand: $('nexo-chat-expand'), messages: $('nexo-chat-messages'),
    mode: $('nexo-chat-mode'), state: $('nexo-chat-state'),
    form: $('nexo-chat-form'), input: $('nexo-chat-text'), counter: $('nexo-chat-counter'),
    send: $('nexo-chat-submit'), suggestions: $('nexo-chat-prompts'),
    aiBox: $('nexo-chat-ia-option'), ai: $('nexo-chat-ia')
  };
  const scope = root.dataset.scope || 'visitante';
  const storageKey = 'nexo_chat_v115_history_' + scope;
  const prefKey = 'nexo_chat_v115_optin_' + scope;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const MAX_SESSIONS = 8;
  const MAX_MESSAGES = 60;
  const MAX_MESSAGE_LENGTH = 2000;
  const recommendations = [
    ['📄 Mi CV', '¿Cómo genero mi CV?'],
    ['👤 Registro', '¿Cómo registro mi cuenta?'],
    ['💼 Ofertas', '¿Cómo funcionan las ofertas laborales?'],
    ['📊 Encuestas', '¿Cómo respondo las encuestas?'],
    ['🏛️ Roles', '¿Qué hacen los roles?'],
    ['🎓 Currícula', '¿Cómo verifico mi currícula?'],
    ['📁 Certificados', '¿Cómo registro certificados?'],
    ['📈 Indicadores', '¿Cómo interpreto los indicadores?']
  ];
  let saveEnabled = false;
  let sessions = [];
  let active = null;
  let busy = false;
  let pending = null;
  let aiEnabled = false;
  let expanded = false;

  function safeStorage(action, key, value) {
    try {
      if (action === 'get') return localStorage.getItem(key);
      if (action === 'set') return localStorage.setItem(key, value);
      if (action === 'remove') return localStorage.removeItem(key);
    } catch (_) { /* incógnito/políticas del navegador: solo usar memoria */ }
    return null;
  }
  function uid() { return 'chat-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 9); }
  function emptySession() { return { id: uid(), created: new Date().toISOString(), title: 'Conversación nueva', topic: '', messages: [] }; }
  function validMessage(m) {
    return m && (m.role === 'user' || m.role === 'assistant') && typeof m.text === 'string'
      && m.text.length <= MAX_MESSAGE_LENGTH && ['guia', 'ia', 'aviso', ''].includes(m.mode || '');
  }
  function fromDisk() {
    try {
      const raw = JSON.parse(safeStorage('get', storageKey) || '[]');
      if (!Array.isArray(raw)) return [];
      return raw.slice(0, MAX_SESSIONS).filter(s => s && typeof s.id === 'string'
        && typeof s.created === 'string' && Array.isArray(s.messages)).map(s => ({
          id: s.id.slice(0, 80), created: s.created.slice(0, 40),
          title: String(s.title || 'Conversación').slice(0, 75),
          topic: typeof s.topic === 'string' ? s.topic.slice(0, 36) : '',
          messages: s.messages.filter(validMessage).slice(-MAX_MESSAGES)
            .map(m => ({role:m.role, text:m.text, mode:m.mode || '', topic:String(m.topic||'').slice(0,36), at: String(m.at || '').slice(0, 40)}))
        }));
    } catch (_) { return []; }
  }
  function persist() {
    if (!saveEnabled) return;
    const clean = sessions.slice(0, MAX_SESSIONS).map(s => ({
      id:s.id, created:s.created, title:s.title, topic:s.topic||'',
      messages:s.messages.slice(-MAX_MESSAGES).map(m => ({ role:m.role, text:m.text.slice(0,MAX_MESSAGE_LENGTH), mode:m.mode || '', topic:m.topic||'', at:m.at }))
    }));
    safeStorage('set', storageKey, JSON.stringify(clean));
  }
  function start() {
    saveEnabled = safeStorage('get', prefKey) === '1';
    ui.save.checked = saveEnabled;
    sessions = saveEnabled ? fromDisk() : [];
    if (!sessions.length) sessions.push(emptySession());
    active = sessions[0];
    drawMessages();
    drawHistory();
    updateCounter();
  }
  function stopReading() { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }
  function show() { ui.panel.hidden = false; ui.open.hidden = true; ui.open.setAttribute('aria-expanded','true'); ui.input.focus(); }
  function hide() { ui.panel.hidden = true; ui.open.hidden = false; ui.open.setAttribute('aria-expanded','false'); closeHistory(); stopReading(); ui.open.focus(); }
  function closeHistory() {
    ui.history.hidden = true;
    root.classList.remove('nexo-chat-history-open');
    ui.historyButton.setAttribute('aria-expanded','false');
  }
  function openHistory() {
    drawHistory(); ui.history.hidden = false;
    root.classList.add('nexo-chat-history-open');
    ui.historyButton.setAttribute('aria-expanded','true');
  }
  function cancelPending() {
    if (pending) { pending.abort(); pending = null; }
    busy = false; ui.send.disabled = false;
    ui.state.textContent = 'Listo';
  }
  function newConversation() {
    cancelPending(); stopReading();
    active = emptySession();
    if (saveEnabled) sessions.unshift(active);
    else sessions = [active];
    sessions = sessions.slice(0, MAX_SESSIONS);
    persist(); closeHistory(); drawMessages(); drawHistory();
    ui.mode.textContent = 'Nuevo chat · Guía institucional';
    ui.input.value = ''; updateCounter(); ui.input.focus();
  }
  function clearAll() {
    if (!window.confirm('¿Eliminar las conversaciones guardadas y limpiar el chat actual?')) return;
    cancelPending(); stopReading();
    safeStorage('remove', storageKey);
    sessions = [emptySession()]; active = sessions[0];
    closeHistory(); drawMessages(); drawHistory();
    ui.mode.textContent = 'Chat limpio · Guía institucional';
    ui.input.value = ''; updateCounter();
  }
  function addMessage(role, text, mode, topic) {
    const msg = { role, text: String(text || '').slice(0, MAX_MESSAGE_LENGTH), mode: mode || '', topic: topic || '', at: new Date().toISOString() };
    active.messages.push(msg);
    if (active.messages.length > MAX_MESSAGES) active.messages.splice(0, active.messages.length - MAX_MESSAGES);
    if (role === 'user' && active.title === 'Conversación nueva') active.title = msg.text.slice(0, 52);
    appendMessage(msg);
    persist();
    return msg;
  }
  function make(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function stepContent(box, text) {
    const parts = String(text).split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    let list = null;
    for (let i=0; i<parts.length; i++) {
      const line = parts[i];
      const numbered = line.match(/^(\d{1,2})[.)]\s+(.+)$/);
      if (numbered) {
        if (!list) { list = make('ol'); box.appendChild(list); }
        const li = make('li','',numbered[2]); list.appendChild(li);
      } else if (i === 0 && /^(GU[IÍ]A|INFORMACI[ÓO]N|¿QU[EÉ]|NEXO ASISTENTE)/i.test(line)) {
        list = null; box.appendChild(make('h4','',line));
      } else {
        list = null;
        const isNote = /^(Consejo|Nota|Importante|Si |No |Recuerda|La informaci[oó]n|Abrir un enlace)/i.test(line);
        box.appendChild(make('p', isNote ? 'nexo-chat-note' : '', line));
      }
    }
  }
  function formattedTime(date) {
    const d = new Date(date); return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('es-PE',{hour:'2-digit',minute:'2-digit'});
  }
  function speak(text) {
    if (!('speechSynthesis' in window)) {
      ui.mode.textContent='La lectura de voz no está disponible en este navegador'; return;
    }
    stopReading();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-PE'; utterance.rate = .95;
    window.speechSynthesis.speak(utterance);
  }
  async function copyText(text, target) {
    try {
      await navigator.clipboard.writeText(text);
      const old = target.textContent; target.textContent = '✓ Copiado';
      setTimeout(() => { if (target.isConnected) target.textContent = old; }, 1400);
    } catch (_) { ui.mode.textContent = 'No se pudo copiar: revisa los permisos del navegador'; }
  }
  function appendMessage(msg) {
    const own = msg.role === 'user';
    const entry = make('article', 'nexo-chat-entry ' + (own?'nexo-chat-own':'nexo-chat-them'));
    const bubble = make('div','nexo-chat-bubble');
    if (own) bubble.textContent = msg.text;
    else stepContent(bubble, msg.text);
    entry.appendChild(bubble);
    const meta = make('div','nexo-chat-entry-meta');
    meta.appendChild(make('span','', (own?'Tú':(msg.mode==='ia'?'NEXO IA':'NEXO Guía')) + ' · ' + formattedTime(msg.at)));
    entry.appendChild(meta);
    if (!own) {
      const tools = make('div','nexo-chat-entry-actions');
      const copy = make('button','nexo-chat-action-mini','⧉ Copiar'); copy.type='button';
      copy.setAttribute('aria-label','Copiar esta respuesta'); copy.addEventListener('click',()=>copyText(msg.text,copy));
      const listen = make('button','nexo-chat-action-mini','🔊 Escuchar'); listen.type='button';
      listen.setAttribute('aria-label','Escuchar esta respuesta'); listen.addEventListener('click',()=>speak(msg.text));
      tools.append(copy, listen);
      if (msg.topic && /^\s*\d+[.)] /m.test(msg.text)) {
        const steps = Array.from(msg.text.matchAll(/^\s*([1-5])[.)] /gm)).map(m => Number(m[1]));
        if (steps.length >= 2) {
          const detail = make('button','nexo-chat-action-mini','☰ Consultar paso');detail.type='button';
          detail.title = 'Abrir los pasos específicos de esta guía';
          const stepChooser = make('div','nexo-chat-step-chooser');stepChooser.hidden = true;
          [...new Set(steps)].forEach(n => {
            const b = make('button','nexo-chat-action-mini','Paso ' + n);b.type='button';
            b.addEventListener('click',()=>ask('Explícame el paso ' + n, msg.topic));
            stepChooser.appendChild(b);
          });
          detail.addEventListener('click',()=>{stepChooser.hidden=!stepChooser.hidden;});
          tools.appendChild(detail);entry.appendChild(stepChooser);
        }
      }
      entry.appendChild(tools);
    }
    ui.messages.appendChild(entry);
    ui.messages.scrollTop = ui.messages.scrollHeight;
  }
  function welcome() {
    const block = make('div','nexo-chat-welcome');
    block.appendChild(make('div','nexo-chat-welcome-icon','✦'));
    block.appendChild(make('strong','', '¡Hola! Soy tu asistente de NEXO UNDAC'));
    block.appendChild(make('p','', 'Te guío con instrucciones claras sobre registro, perfil, CV, certificados, ofertas, encuestas y roles. Puedes elegir un tema abajo o escribir tu pregunta.'));
    block.appendChild(make('p','', 'Tus conversaciones NO se guardan automáticamente. Para conservarlas, activa la opción en Historial.'));
    return block;
  }
  function drawMessages() {
    ui.messages.replaceChildren();
    if (!active.messages.length) ui.messages.appendChild(welcome());
    else active.messages.forEach(appendMessage);
  }
  function drawHistory() {
    ui.historyList.replaceChildren();
    ui.save.checked = saveEnabled;
    if (!saveEnabled) {
      ui.historyList.appendChild(make('p','nexo-chat-history-empty','El historial está desactivado. Activa el guardado arriba si deseas conservar conversaciones en este navegador.'));
      return;
    }
    const visible = sessions.filter(s=>s.messages.length);
    if (!visible.length) ui.historyList.appendChild(make('p','nexo-chat-history-empty','Todavía no hay conversaciones guardadas.'));
    for (const s of visible) {
      const line = make('div','nexo-chat-session' + (s.id===active.id?' active':''));
      const btn = make('button','nexo-chat-session-open',s.title);btn.type='button';
      btn.setAttribute('aria-label','Abrir conversación '+s.title);
      const date=make('small','',new Date(s.created).toLocaleString('es-PE',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}));
      btn.appendChild(date);
      btn.addEventListener('click',()=>{ active=s; closeHistory(); drawMessages(); ui.input.focus(); });
      const del=make('button','nexo-chat-session-delete','✕');del.type='button';
      del.title='Eliminar conversación';del.setAttribute('aria-label','Eliminar conversación '+s.title);
      del.addEventListener('click',()=>{
        if (!window.confirm('¿Eliminar esta conversación guardada?')) return;
        sessions=sessions.filter(x=>x.id!==s.id);
        if (active.id===s.id) active=sessions[0] || emptySession();
        if(!sessions.length) sessions.push(active);
        persist(); drawHistory(); drawMessages();
      });
      line.append(btn,del); ui.historyList.appendChild(line);
    }
  }
  function updateCounter() {
    ui.counter.textContent=ui.input.value.length+' / 300';
    ui.counter.style.color=ui.input.value.length>270?'#b85133':'';
  }
  function refreshSuggestions(q) {
    let items = recommendations.slice(0,5);
    const norm=String(q||'').toLowerCase();
    if (/cv|curr[íi]cul|hoja de vida/.test(norm)) items=[recommendations[6],recommendations[7],recommendations[2],recommendations[3]];
    else if (/oferta|postul|empleo|trabajo/.test(norm)) items=[recommendations[7],recommendations[2],recommendations[6],recommendations[3]];
    else if (/registr|cuenta|perfil|acceder/.test(norm)) items=[recommendations[5],recommendations[0],recommendations[4],recommendations[3]];
    ui.suggestions.replaceChildren(...items.map(([label,question])=>{
      const b=make('button','',label);b.type='button';b.dataset.question=question;return b;
    }));
  }
  function sensitive(text) {
    return /(?:^|\D)\d{8}(?:\D|$)/.test(text) || /(?:AIza[A-Za-z0-9_-]{15,}|AQ\.[A-Za-z0-9_-]{15,})/.test(text);
  }
  async function ask(question, contextOverride) {
    if (busy) return;
    const text=String(question||'').trim();
    if (!text) return;
    if (text.length>300) { ui.mode.textContent='Máximo 300 caracteres por pregunta';return; }
    if (sensitive(text)) { ui.mode.textContent='No envíes números de DNI ni claves privadas en el chat';return; }
    if (!ui.history.hidden) closeHistory();
    const useAI=!!(aiEnabled && ui.ai.checked);
    const conversationId=active.id;
    const requestTopic=typeof contextOverride==='string'?contextOverride:(active.topic || '');
    addMessage('user',text,''); ui.input.value='';updateCounter();refreshSuggestions(text);
    busy=true;ui.send.disabled=true;ui.state.textContent='Procesando';ui.mode.textContent='Buscando la guía adecuada…';
    const controller=new AbortController();pending=controller;
    try {
      const res=await fetch(root.dataset.api,{
        method:'POST',credentials:'same-origin',signal:controller.signal,
        headers:{'Content-Type':'application/json','X-CSRFToken':csrf},
        body:JSON.stringify({mensaje:text,contexto_tema:requestTopic,usar_ia:useAI,consentimiento:useAI})
      });
      const result=await res.json().catch(()=>({}));
      if (!res.ok) throw Error(result.error||'HTTP '+res.status);
      if (conversationId!==active.id) return;
      const answer=String(result.respuesta||'No se encontró información confirmada.');
      const newTopic=typeof result.tema==='string' ? result.tema : '';
      if (newTopic) active.topic=newTopic;
      addMessage('assistant',answer,result.modo==='ia'?'ia':'guia',newTopic);
      ui.mode.textContent=result.modo==='ia'?'Respuesta reformulada con Gemini':'Respuesta de la guía institucional';
      if (result.aviso) addMessage('assistant',String(result.aviso),'aviso');
      if (useAI) ui.ai.checked=false;
    } catch (error) {
      if (error.name!=='AbortError' && conversationId===active.id) {
        const msg=/Límite|limite|429/.test(error.message)?error.message:'No se pudo completar la consulta. Comprueba la conexión con NEXO UNDAC.';
        addMessage('assistant',msg,'aviso'); ui.mode.textContent='Servicio temporalmente no disponible';
      }
    } finally {
      if (pending===controller) {pending=null;busy=false;ui.send.disabled=false;ui.state.textContent='En línea';}
      if (!ui.panel.hidden && ui.history.hidden) ui.input.focus();
    }
  }
  function exportActive() {
    if (!active.messages.length) {ui.mode.textContent='Primero realiza una consulta para exportar';closeHistory();return;}
    const txt = ['NEXO UNDAC · Conversación del asistente', 'Exportado: '+new Date().toLocaleString('es-PE'), '---',
      ...active.messages.map(m => (m.role==='user'?'Usuario':'Asistente') + ' (' + (formattedTime(m.at)||'') + '):\n' + m.text + '\n')].join('\n');
    const url=URL.createObjectURL(new Blob([txt],{type:'text/plain;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download='nexo-undac-conversacion.txt';document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),800);
  }
  ui.open.addEventListener('click',show);
  ui.close.addEventListener('click',hide);
  ui.new.addEventListener('click',newConversation);
  ui.historyButton.addEventListener('click',()=>ui.history.hidden?openHistory():closeHistory());
  ui.historyClose.addEventListener('click',()=>{closeHistory();ui.input.focus();});
  ui.clear.addEventListener('click',clearAll);
  ui.export.addEventListener('click',exportActive);
  ui.expand.addEventListener('click',()=>{
    expanded=!expanded;root.classList.toggle('nexo-chat-wide',expanded);
    ui.expand.setAttribute('aria-pressed',String(expanded));
    ui.expand.setAttribute('aria-label',expanded?'Reducir ventana':'Ampliar ventana');
    ui.expand.title=expanded?'Reducir ventana':'Ampliar ventana';
  });
  ui.save.addEventListener('change',()=>{
    if (ui.save.checked) {
      saveEnabled=true;safeStorage('set',prefKey,'1');
      sessions=[active];persist();
    } else {
      if(!window.confirm('¿Desactivar el guardado y eliminar las conversaciones guardadas de este navegador?')){
        ui.save.checked=true;return;
      }
      saveEnabled=false;safeStorage('remove',prefKey);safeStorage('remove',storageKey);
      sessions=[active];
    }
    drawHistory();
  });
  ui.form.addEventListener('submit',event=>{event.preventDefault();ask(ui.input.value);});
  ui.input.addEventListener('input',updateCounter);
  ui.input.addEventListener('keydown',event=>{
    if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();if(!busy)ui.form.requestSubmit();}
  });
  ui.suggestions.addEventListener('click',event=>{
    const b=event.target.closest('[data-question]');if(b)ask(b.dataset.question);
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!ui.panel.hidden){
      if(!ui.history.hidden)closeHistory();else hide();
    }
  });
  fetch(root.dataset.estado,{credentials:'same-origin'})
    .then(r=>r.ok?r.json():{})
    .then(result=>{
      if(result.ia_habilitada){aiEnabled=true;ui.aiBox.hidden=false;ui.mode.textContent='Guía institucional · IA opcional autorizada';}
    }).catch(()=>{ui.state.textContent='Guía local';});
  start();
})();
