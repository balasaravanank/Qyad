/* Student Qyad - MVP frontend v6. No build step; plain fetch + DOM.
   v6: Qyad, light/dark appearance, collapsible navigation and responsive full-width pages. */
const root = document.getElementById('root');
let me = null, spaces = [], view = { name: 'today' };
let authConfig = {}, clerkMode = false, clerkReady = null;

const APP_STATUSES = ['saved','applied','assessment','interview','offer','rejected'];
const STATUS_LABEL = { open:'Open', in_progress:'In progress', done:'Done', archived:'Archived' };
const APP_STATUS_LABEL = { saved:'Saved', applied:'Applied', assessment:'Assessment', interview:'Interview', offer:'Offer', rejected:'Rejected' };
const APP_STATUS_COLOR = { saved:'chip-stone', applied:'chip-blue', assessment:'chip-college', interview:'chip-group', offer:'chip-green', rejected:'chip-red' };

/* ---------- helpers ---------- */
async function api(path, opts = {}) {
  if (opts.body && typeof opts.body !== 'string' && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
    opts.headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  }
  if(clerkMode && window.Clerk?.session){const token=await window.Clerk.session.getToken();if(token)opts.headers={...(opts.headers||{}),Authorization:'Bearer '+token};}
  const res = await fetch('/api/v1' + path, opts);
  if (res.status === 401 && !path.startsWith('/auth')) { renderAuth(); throw new Error('auth'); }
  if (!res.ok) {
    let msg = res.status;
    try { msg = (await res.json()).detail || msg; } catch (e) {}
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return res.json();
}
function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML.replaceAll('"','&quot;').replaceAll("'",'&#39;'); }
function h(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; }
function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso.length === 10 ? iso + 'T00:00:00' : iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
function fmtDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ', ' +
         d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}
function relDue(iso) {
  if (!iso) return null;
  const today = new Date(); today.setHours(0,0,0,0);
  const d = new Date(iso + 'T00:00:00');
  const diff = Math.round((d - today) / 86400000);
  if (diff < 0) return { text: Math.abs(diff) + 'd overdue', cls: 'text-red-600' };
  if (diff === 0) return { text: 'Due today', cls: 'text-amber-600' };
  if (diff === 1) return { text: 'Due tomorrow', cls: 'text-stone-500' };
  return { text: 'Due ' + fmtDate(iso), cls: 'text-stone-500' };
}
const AV_COLORS = ['bg-brand-500','bg-rose-500','bg-emerald-500','bg-amber-500','bg-sky-500','bg-violet-500','bg-teal-500','bg-orange-500'];
function avatar(name, size = 'w-7 h-7 text-[11px]') {
  const n = (name || '?').trim();
  const initials = n.split(/\s+/).slice(0,2).map(w => w[0]).join('').toUpperCase() || '?';
  let hash = 0; for (const c of n) hash = (hash * 31 + c.charCodeAt(0)) >>> 0;
  return `<span class="${size} ${AV_COLORS[hash % AV_COLORS.length]} rounded-full inline-flex items-center justify-center text-white font-semibold shrink-0">${esc(initials)}</span>`;
}

/* ---------- icons (lucide-style inline svg) ---------- */
function icon(name, cls = 'w-[18px] h-[18px]') {
  const P = {
    today: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M17.5 14.5c2.1.7 3.5 2.7 3.5 5.5"/>',
    cap: '<path d="M2 9l10-4 10 4-10 4z"/><path d="M6 11v5.5c0 1.5 2.7 3 6 3s6-1.5 6-3V11"/><path d="M22 9v5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.2 3h-4l-.4 2.7a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.4 2.7h4l.4-2.7a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v5M16 3v5M3 10h18"/>',
    brief: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    spark: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5 5h14l3 7v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-7z"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/>',
    logout: '<path d="M9 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    flag: '<path d="M4 22V5c4-2 8 2 12 0v10c-4 2-8-2-12 0"/>',
    dots: '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
    send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  };
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${P[name] || ''}</svg>`;
}

/* ---------- chips ---------- */
function privacyChip(label) {
  const cls = label === 'Private' ? 'chip-private' : (label === 'College' || /college/i.test(label) ? 'chip-college' : 'chip-group');
  const ic = label === 'Private' ? icon('lock', 'w-3 h-3') : '';
  return `<span class="chip ${cls}">${ic}${esc(label)}</span>`;
}
function statusChip(status) {
  const map = { open:['chip-stone','Open'], in_progress:['chip-blue','In progress'], done:['chip-green','Done'], archived:['chip-stone','Archived'] };
  const [cls, label] = map[status] || map.open;
  return `<span class="chip ${cls}">${label}</span>`;
}
function appStatusChip(st) { return `<span class="chip ${APP_STATUS_COLOR[st] || 'chip-stone'}">${APP_STATUS_LABEL[st] || st}</span>`; }
function kindChip(k) {
  const map = { status:'chip-stone', announcement:'chip-college', progress:'chip-group' };
  return `<span class="chip ${map[k] || 'chip-stone'}">${esc(k)}</span>`;
}

/* ---------- toast ---------- */
function toast(msg, kind = 'ok') {
  let wrap = document.getElementById('toasts');
  if (!wrap) { wrap = h('<div id="toasts" class="fixed bottom-20 md:bottom-6 right-4 z-[70] flex flex-col gap-2 items-end"></div>'); document.body.appendChild(wrap); }
  const t = h(`<div class="toast-in flex items-center gap-2 bg-stone-900 text-white text-sm font-medium pl-3 pr-4 py-2.5 rounded-xl shadow-pop max-w-xs">
    <span class="${kind === 'err' ? 'text-red-400' : 'text-emerald-400'}">${icon(kind === 'err' ? 'x' : 'check', 'w-4 h-4')}</span>${esc(msg)}</div>`);
  wrap.appendChild(t);
  setTimeout(() => { t.style.transition = 'opacity .3s'; t.style.opacity = '0'; setTimeout(() => t.remove(), 320); }, 3200);
}

/* ---------- modal + confirm ---------- */
function openModal(html, wide) {
  closeModal();
  const ov = h(`<div class="modal-overlay fixed inset-0 z-50 bg-stone-900/40 backdrop-blur-[2px] flex items-end sm:items-center justify-center p-0 sm:p-6">
    <div class="modal-card bg-white w-full ${wide ? 'sm:max-w-2xl' : 'sm:max-w-md'} rounded-t-2xl sm:rounded-2xl shadow-pop max-h-[92vh] overflow-y-auto"></div></div>`);
  ov.firstElementChild.innerHTML = html;
  ov.addEventListener('mousedown', e => { if (e.target === ov) closeModal(); });
  document.body.appendChild(ov);
  ov.querySelectorAll('[data-close]').forEach(b => b.onclick = closeModal);
  return ov.firstElementChild;
}
function closeModal() { const o = document.querySelector('.modal-overlay'); if (o) o.remove(); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

function confirmDlg({ title, body, actionLabel = 'Delete', danger = true }) {
  return new Promise(resolve => {
    const m = openModal(`
      <div class="p-6">
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-full ${danger ? 'bg-red-50 text-red-500' : 'bg-brand-50 text-brand-500'} flex items-center justify-center shrink-0">${icon(danger ? 'trash' : 'arrow', 'w-5 h-5')}</div>
          <div class="min-w-0"><h3 class="font-bold text-lg">${esc(title)}</h3>
          <p class="text-sm text-stone-500 mt-1">${body}</p></div>
        </div>
        <div class="flex justify-end gap-2 mt-6">
          <button class="btn-ghost" data-close>Cancel</button>
          <button id="cfok" class="${danger ? 'btn-danger' : 'btn-primary'}">${esc(actionLabel)}</button>
        </div>
      </div>`);
    m.querySelector('#cfok').onclick = () => { closeModal(); resolve(true); };
    m.addEventListener('mousedown', e => { if (e.target.closest('.modal-overlay') === e.target.closest('.modal-overlay')) {} });
    m.closest('.modal-overlay').addEventListener('mousedown', () => resolve(false), { once: true });
  });
}

/* ---------- auth ---------- */
function renderAuth(mode = 'login') {
  root.innerHTML = '';
  if(authConfig.auth_mode==='clerk') {
    root.innerHTML='<main class="auth-required"><div class="card"><span class="auth-mark">Q</span><h1>Sign in to Qyad</h1><p>Your plans. Your next opportunity.</p><button id="clerk-login" class="btn-primary">Continue with Clerk</button><p id="auth-error" role="alert"></p><p class="auth-footnote">Authentication by Clerk. Your workspace data stays on the Qyad server.</p></div></main>';
    document.getElementById('clerk-login').onclick=()=>openClerk(false);
    return;
  }
  const isLogin = mode === 'login';
  root.appendChild(h(`
  <div class="min-h-screen flex">
    <div class="hidden lg:flex w-[44%] login-art text-stone-900 flex-col justify-between p-12 relative overflow-hidden">
      <div class="blob absolute -top-24 -right-24 w-96 h-96 rounded-full bg-brand-300/60"></div>
      <div class="blob absolute bottom-10 -left-16 w-72 h-72 rounded-full bg-brand-200/70"></div>
      <div class="relative flex items-center gap-2.5 font-bold text-lg">
        <span class="w-9 h-9 rounded-xl bg-brand-500 text-white flex items-center justify-center">${icon('grid','w-5 h-5')}</span> Qyad
      </div>
      <div class="relative">
        <h2 class="text-3xl font-extrabold leading-tight tracking-tight">Private plans, team hunts,<br>college stuff. One place.</h2>
        <ul class="mt-8 space-y-4 text-stone-600 text-sm">
          <li class="flex items-center gap-3"><span class="w-9 h-9 rounded-full bg-white/70 ring-1 ring-brand-200 flex items-center justify-center text-brand-600 shrink-0">${icon('lock','w-4.5 h-4.5 w-[18px] h-[18px]')}</span> A private space only you can see</li>
          <li class="flex items-center gap-3"><span class="w-9 h-9 rounded-full bg-white/70 ring-1 ring-brand-200 flex items-center justify-center text-brand-600 shrink-0">${icon('users','w-[18px] h-[18px]')}</span> Groups for internship links and updates with friends</li>
          <li class="flex items-center gap-3"><span class="w-9 h-9 rounded-full bg-white/70 ring-1 ring-brand-200 flex items-center justify-center text-brand-600 shrink-0">${icon('cap','w-[18px] h-[18px]')}</span> A separate space for college work</li>
          <li class="flex items-center gap-3"><span class="w-9 h-9 rounded-full bg-white/70 ring-1 ring-brand-200 flex items-center justify-center text-brand-600 shrink-0">${icon('mic','w-[18px] h-[18px]')}</span> Voice updates through your own assistant</li>
        </ul>
      </div>
      <div class="relative text-xs text-stone-500">MVP build - voice connection unverified</div>
    </div>
    <div class="flex-1 flex items-center justify-center p-6 relative">
      <div class="w-full max-w-sm">
        <div class="flex items-center gap-2.5 font-bold text-lg mb-8 lg:hidden">
          <span class="w-9 h-9 rounded-xl bg-brand-600 text-white flex items-center justify-center">${icon('grid','w-5 h-5')}</span> Qyad
        </div>
        <h1 class="text-2xl font-bold">${isLogin ? 'Welcome back' : 'Create your account'}</h1>
        <p class="text-sm text-stone-500 mt-1 mb-6">${isLogin ? 'Log in to your workspace.' : 'Your private space is created automatically.'}</p>
        <button id="clerk-login" class="btn-ghost w-full mb-4 ${authConfig.clerk_enabled?'':'hidden'}">Continue with Clerk</button>
        <form id="f" class="space-y-3">
          ${isLogin ? '' : `<div><label class="label">Name</label><input id="name" required placeholder="Your name" class="input"></div>`}
          <div><label class="label">Email</label><input id="email" type="email" required placeholder="you@example.com" class="input"></div>
          <div><label class="label">Password</label><input id="pw" type="password" required placeholder="Min 6 characters" class="input"></div>
          <button class="btn-primary w-full !py-2.5">${isLogin ? 'Log in' : 'Create account'}</button>
        </form>
        <p class="text-sm text-stone-500 mt-5 text-center">${isLogin ? 'No account?' : 'Have an account?'}
          <a href="#" id="swap" class="text-brand-600 font-semibold">${isLogin ? 'Sign up' : 'Log in'}</a></p>
        <p id="err" class="text-sm text-red-600 mt-3 text-center"></p>
      </div>
    </div>
  </div>`));
  document.getElementById('clerk-login').onclick=()=>openClerk(false);
  document.getElementById('swap').onclick = e => { e.preventDefault(); renderAuth(isLogin ? 'register' : 'login'); };
  document.getElementById('f').onsubmit = async e => {
    e.preventDefault();
    try {
      const body = { email: document.getElementById('email').value, password: document.getElementById('pw').value };
      if (!isLogin) body.name = document.getElementById('name').value;
      savePreference('qyad-auth-provider','local');clerkMode=false;me = await api('/auth/' + (isLogin ? 'login' : 'register'), { method: 'POST', body });
      await boot();
    } catch (err) { document.getElementById('err').textContent = err.message; }
  };
}

/* ---------- shell ---------- */
async function boot() {
  const join=new URLSearchParams(location.search).get('join');
  if(join){try{await api('/invites/'+encodeURIComponent(join)+'/accept',{method:'POST'});history.replaceState(null,'','/');toast('Joined the space');}catch(e){toast('Invite failed: '+e.message,'err');}}
  spaces = await api('/spaces');
  renderShell();
  go('today');
}

function stored(key, fallback) { try{return localStorage.getItem(key)||fallback;}catch(e){return fallback;} }
function savePreference(key,value){try{localStorage.setItem(key,value);}catch(e){}}
function applyTheme(value){document.documentElement.dataset.theme=value;savePreference('qyad-theme',value);document.querySelectorAll('[data-theme-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.themeChoice===value)));const b=document.getElementById('theme-toggle');if(b){b.innerHTML=icon(value==='dark'?'sun':'moon');b.title=value==='dark'?'Switch to light mode':'Switch to dark mode';b.setAttribute('aria-label',b.title);}}
function toggleSidebar(){const value=document.documentElement.dataset.sidebar==='collapsed'?'expanded':'collapsed';document.documentElement.dataset.sidebar=value;savePreference('qyad-sidebar',value);const b=document.getElementById('sidebar-toggle');if(b){b.setAttribute('aria-expanded',String(value!=='collapsed'));b.title=value==='collapsed'?'Expand sidebar':'Collapse sidebar';}}
function navHtml() {
  const groups = spaces.filter(s => s.type === 'group');
  const colleges = spaces.filter(s => s.type === 'college');
  const item = (key, ic, label, chip = '') =>
    `<div class="navitem ${view.name === key || (key === 'my' && view.name === 'my') ? 'active' : ''}" role="button" tabindex="0" title="${label}" aria-label="${label}" data-nav="${key}">${icon(ic)}<span class="flex-1 truncate">${label}</span>${chip}</div>`;
  const sp = s => `<div class="navitem ${view.name === 'space' && view.arg === s.id ? 'active' : ''}" role="button" tabindex="0" title="${esc(s.name)}" aria-label="${esc(s.name)}" data-nav="space:${s.id}">
      ${icon(s.type === 'college' ? 'cap' : 'users')}<span class="flex-1 truncate">${esc(s.name)}</span>
      <span class="text-[11px] text-stone-400 font-medium">${s.member_count || ''}</span></div>`;
  return `
    <div class="brand-row flex items-center gap-2.5 px-3 pt-5 pb-6 font-bold text-[17px]">
      <span class="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center">${icon('grid','w-[18px] h-[18px]')}</span><span class="brand-name">Qyad</span>
    </div>
    <nav class="px-3 space-y-0.5">
      ${item('today', 'today', 'Today')}
      ${item('my', 'lock', 'My Space', '<span class="chip chip-private">Private</span>')}
    </nav>
    <div class="nav-heading px-5 pt-5 pb-1 text-[11px] font-bold uppercase tracking-wider text-stone-400">Groups</div>
    <nav class="px-3 space-y-0.5">${groups.map(sp).join('') || '<p class="px-3 text-xs text-stone-400">No groups yet</p>'}</nav>
    <div class="nav-heading px-5 pt-4 pb-1 text-[11px] font-bold uppercase tracking-wider text-stone-400">College</div>
    <nav class="px-3 space-y-0.5">${colleges.map(sp).join('') || '<p class="px-3 text-xs text-stone-400">No college space yet</p>'}</nav>
    <div class="px-3 pt-2"><div class="navitem text-brand-600 hover:!bg-brand-50" role="button" tabindex="0" title="New space" aria-label="New space" data-nav="newspace">${icon('plus')}<span>New space</span></div></div>
    <div class="flex-1"></div><p class="app-version">Qyad v0.9.2 · API v1</p>
    <nav class="px-3 pb-2">${item('settings', 'gear', 'Settings')}</nav>
    <div class="sidebar-user mx-3 mb-3 p-3 rounded-xl bg-stone-50 ring-1 ring-stone-200/70 flex items-center gap-2.5">
      ${avatar(me.name, 'w-8 h-8 text-xs')}
      <div class="min-w-0 flex-1"><div class="text-sm font-semibold truncate">${esc(me.name)}</div>
      <div class="text-[11px] text-stone-400 truncate">${esc(me.email)}</div></div>
      <button id="logout" title="Log out" class="text-stone-400 hover:text-stone-700">${icon('logout','w-4 h-4')}</button>
    </div>`;
}

function renderShell() {
  root.innerHTML = '';
  root.appendChild(h(`
  <div class="flex min-h-screen">
    <aside id="sidebar" aria-label="Main navigation" class="hidden md:flex w-64 glass-side bg-white border-r border-stone-200 flex-col shrink-0 sticky top-0 h-screen overflow-y-auto">${navHtml()}</aside>
    <div class="flex-1 min-w-0 flex flex-col">
      <header class="md:hidden sticky top-0 z-40 glass-bar bg-white/90 backdrop-blur border-b border-stone-200 px-4 py-3 flex items-center gap-2.5">
        <span class="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center">${icon('grid','w-[18px] h-[18px]')}</span>
        <span class="font-bold">Qyad <small class="text-xs text-stone-500">v0.9.2</small></span>
        <div class="flex-1"></div>
        ${avatar(me.name, 'w-8 h-8 text-xs')}
      </header>
      <div class="desktop-toolbar hidden md:flex items-center gap-3 px-6 lg:px-10 py-3 border-b border-stone-200"><button id="sidebar-toggle" class="icon-button" aria-label="Toggle sidebar" aria-expanded="${document.documentElement.dataset.sidebar!=='collapsed'}" title="Collapse sidebar"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/></svg></button><span class="text-xs text-stone-400">Qyad <span class="mx-2">/</span> <span class="text-stone-600">${esc(view.name==='space'?(spaces.find(s=>s.id===view.arg)?.name||'Team space'):({my:'My Space',today:'Today',settings:'Settings',spaces:'Spaces'}[view.name]||'Home'))}</span></span><div class="flex-1"></div><span class="text-[11px] text-stone-400">Your space to move forward</span><button id="theme-toggle" class="icon-button" aria-label="Switch appearance" title="Switch appearance">${icon('moon')}</button></div>
      <main id="main" class="flex-1 w-full mx-auto px-4 sm:px-6 lg:px-10 py-6 pb-28 md:pb-10"></main>
    </div>
    <nav class="md:hidden fixed bottom-0 inset-x-0 z-40 glass-bar bg-white border-t border-stone-200 flex justify-around py-1.5" style="padding-bottom: env(safe-area-inset-bottom)">
      ${[['today','today','Today'],['my','lock','My Space'],['spaces','users','Spaces'],['settings','gear','Settings']].map(([k,ic,l]) =>
        `<button data-mnav="${k}" class="flex flex-col items-center gap-0.5 px-3 py-1 text-[10px] font-medium ${(view.name===k)||(k==='spaces'&&view.name==='space')||(k==='spaces'&&view.name==='spaces') ? 'text-brand-600' : 'text-stone-400'}">${icon(ic,'w-5 h-5')}${l}</button>`).join('')}
    </nav>
  </div>`));
  root.querySelectorAll('[data-nav]').forEach(b => b.onclick = () => nav(b.dataset.nav));
  root.querySelectorAll('[data-mnav]').forEach(b => b.onclick = () => nav(b.dataset.mnav));
  root.querySelectorAll('[data-nav]').forEach(b=>b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();nav(b.dataset.nav);}});
  const collapse=document.getElementById('sidebar-toggle');if(collapse)collapse.onclick=toggleSidebar;
  const theme=document.getElementById('theme-toggle');if(theme)theme.onclick=()=>applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');
  applyTheme(document.documentElement.dataset.theme||'light');
  const lo = document.getElementById('logout');
  if (lo) lo.onclick = async () => { await api('/auth/logout', { method: 'POST' });if(window.Clerk?.session)await window.Clerk.signOut();savePreference('qyad-auth-provider','local');clerkMode=false;location.reload(); };
}

function nav(n) {
  if (n === 'newspace') return openNewSpace();
  if (n === 'spaces') return go('spaces');
  if (n.startsWith('space:')) return go('space', n.slice(6));
  go(n);
}

function main() { return document.getElementById('main'); }

async function go(name, arg) {
  view = { name, arg };
  renderShell();
  if (name === 'today') {await renderToday();return appendStarterOpportunities();}
  if (name === 'my') return renderMySpace(view.tab || 'todos');
  if (name === 'spaces') return renderSpaceList();
  if (name === 'space') return renderSpace(arg, 'opportunities');
  if (name === 'settings') return renderSettings();
}

function openNewSpace() {
  const m = openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-bold text-lg">New space</h3>
        <button data-close class="text-stone-400 hover:text-stone-700">${icon('x','w-5 h-5')}</button>
      </div>
      <form id="ns" class="space-y-4">
        <div><label class="label">Name</label><input id="nsname" required class="input" placeholder="e.g. Internship Hunt"></div>
        <div><label class="label">Type</label>
          <div class="grid grid-cols-2 gap-2">
            <label class="card p-3 cursor-pointer has-[:checked]:ring-2 has-[:checked]:ring-brand-500">
              <input type="radio" name="nstype" value="group" checked class="sr-only">
              <div class="flex items-center gap-2 font-semibold text-sm">${icon('users','w-4 h-4')} Group</div>
              <p class="text-xs text-stone-500 mt-1">Internship links, updates and projects with friends.</p></label>
            <label class="card p-3 cursor-pointer has-[:checked]:ring-2 has-[:checked]:ring-brand-500">
              <input type="radio" name="nstype" value="college" class="sr-only">
              <div class="flex items-center gap-2 font-semibold text-sm">${icon('cap','w-4 h-4')} College</div>
              <p class="text-xs text-stone-500 mt-1">College work, kept apart from job hunting.</p></label>
          </div></div>
        <button class="btn-primary w-full">Create space</button>
      </form>
    </div>`);
  m.querySelector('#ns').onsubmit = async e => {
    e.preventDefault();
    const name = m.querySelector('#nsname').value;
    const type = m.querySelector('input[name=nstype]:checked').value;
    const s = await api('/spaces', { method: 'POST', body: { name, type } });
    spaces = await api('/spaces');
    closeModal();
    toast('Space created');
    go('space', s.id);
  };
}

function renderSpaceList() {
  const all = spaces.filter(s => s.type !== 'personal');
  main().innerHTML = `
    <div class="view-in">
      <h1 class="text-2xl font-bold mb-1">Spaces</h1>
      <p class="text-sm text-stone-500 mb-6">Your groups and college spaces.</p>
      <div class="grid gap-3 sm:grid-cols-2 stagger">
        ${all.map(s => `<button data-open="${s.id}" class="card p-5 text-left hover:shadow-pop transition-shadow">
          <div class="flex items-center gap-3">
            <span class="w-10 h-10 rounded-xl ${s.type === 'college' ? 'bg-violet-100 text-violet-600' : 'bg-sky-100 text-sky-600'} flex items-center justify-center">${icon(s.type === 'college' ? 'cap' : 'users','w-5 h-5')}</span>
            <div class="min-w-0"><div class="font-semibold truncate">${esc(s.name)}</div>
            <div class="text-xs text-stone-500">${s.member_count || 1} member(s)</div></div>
          </div></button>`).join('')}
        <button id="nsbtn" class="rounded-xl border-2 border-dashed border-stone-300 p-5 text-left text-stone-400 hover:border-brand-400 hover:text-brand-500 transition-colors">
          <div class="flex items-center gap-3">${icon('plus','w-5 h-5')}<span class="font-semibold text-sm">New space</span></div>
        </button>
      </div>
    </div>`;
  main().querySelectorAll('[data-open]').forEach(b => b.onclick = () => go('space', b.dataset.open));
  document.getElementById('nsbtn').onclick = openNewSpace;
}

/* ---------- Today ---------- */
function taskCard(i, opts = {}) {
  const due = relDue(i.due_date);
  const done = i.status === 'done';
  return `
  <div class="card p-3.5 mb-2 flex items-center gap-3 hover:shadow-pop transition-shadow cursor-pointer" data-item="${i.id}">
    <button data-done="${i.id}" title="${done ? 'Reopen' : 'Mark done'}"
      class="w-5 h-5 rounded-full border-2 ${done ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-stone-300 hover:border-emerald-500 text-transparent'} flex items-center justify-center shrink-0 transition-colors">${icon('check','w-3 h-3')}</button>
    <div class="flex-1 min-w-0">
      <div class="font-medium text-[15px] truncate ${done ? 'line-through text-stone-400' : ''}">${esc(i.title)}</div>
      <div class="text-xs mt-0.5 ${due ? due.cls : 'text-stone-400'}">${due ? due.text : 'No date'}</div>
    </div>
    ${statusChip(i.status)}
    ${privacyChip(opts.label || i.space_label || 'Private')}
  </div>`;
}

async function renderToday() {
  const t = await api('/today');
  const d = new Date(t.date + 'T00:00:00');
  const greeting = d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  const stat = (n, l, ic, tone) => `
    <div class="card px-4 py-4 flex items-center gap-3">
      <span class="w-10 h-10 rounded-xl ${tone.bg} ${tone.fg} flex items-center justify-center shrink-0">${icon(ic, 'w-5 h-5')}</span>
      <div><div class="text-2xl font-extrabold tracking-tight ${tone.num}">${n}</div>
      <div class="text-xs text-stone-500 font-medium">${l}</div></div>
    </div>`;
  const tones = {
    red: { bg: 'bg-red-50', fg: 'text-red-500', num: t.overdue.length ? 'text-red-600' : '' },
    amber: { bg: 'bg-amber-50', fg: 'text-amber-500', num: t.due_today.length ? 'text-amber-600' : '' },
    brand: { bg: 'bg-brand-50', fg: 'text-brand-500', num: t.application_actions.length ? 'text-brand-600' : '' },
  };
  const empty = (msg) => `<div class="rounded-xl border-2 border-dashed border-stone-200 p-6 text-center text-sm text-stone-400">${msg}</div>`;
  const appAction = a => `
      <div class="card p-3.5 mb-2 flex items-center gap-3 cursor-pointer hover:shadow-pop transition-shadow" data-app="${a.id}">
        <span class="w-9 h-9 rounded-lg bg-brand-50 text-brand-500 flex items-center justify-center shrink-0">${icon('brief','w-4 h-4')}</span>
        <div class="flex-1 min-w-0">
          <div class="font-medium text-[15px] truncate">${esc(a.next_action)}</div>
          <div class="text-xs text-stone-500 truncate">${esc(a.title)}${a.company ? ' · ' + esc(a.company) : ''}${a.deadline ? ' · deadline ' + fmtDate(a.deadline) : ''}</div>
        </div>
        ${appStatusChip(a.status)}
        ${privacyChip('Private')}
      </div>`;
  const taskSections =
    (t.overdue.length ? `<h2 class="text-xs font-bold text-red-600 uppercase tracking-widest mb-2 mt-1">Overdue</h2><div class="mb-5 stagger">${t.overdue.map(i => taskCard(i)).join('')}</div>` : '') +
    (t.due_today.length ? `<h2 class="text-xs font-bold text-amber-600 uppercase tracking-widest mb-2">Due today</h2><div class="mb-5 stagger">${t.due_today.map(i => taskCard(i)).join('')}</div>` : '') +
    `<h2 class="text-xs font-bold text-stone-400 uppercase tracking-widest mb-2">Upcoming</h2>
     <div class="mb-5 stagger">${t.upcoming.length ? t.upcoming.map(i => taskCard(i)).join('') : empty('Nothing else open. Add a todo in My Space.')}</div>`;
  const actions = t.application_actions.length;
  main().innerHTML = `
  <div class="view-in">
    <div class="flex flex-wrap items-end justify-between gap-3 mb-6">
      <div>
        <p class="text-sm font-medium text-stone-500">${greeting}</p>
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight">Good day, ${esc(me.name.split(' ')[0])}</h1>
      </div>
      <button id="quickadd" class="btn-primary">${icon('plus','w-4 h-4')} Quick add</button>
    </div>
    <div class="grid grid-cols-3 gap-3 mb-6 stagger">
      ${stat(t.overdue.length, 'Overdue', 'flag', tones.red)}
      ${stat(t.due_today.length, 'Due today', 'clock', tones.amber)}
      ${stat(t.application_actions.length, 'App actions', 'brief', tones.brand)}
    </div>
    <section class="card p-5 mb-6">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2"><h2 class="font-bold flex items-center gap-2">${icon('cal','w-4 h-4')} Opportunity deadlines</h2><span class="chip chip-blue">Next 7 days + overdue</span></div>
      <p class="text-xs text-stone-500 mb-4">Shared links needing a decision, and saved private applications. In-app visibility only, no phone reminders.</p>
      <div class="stagger">
      ${[...(t.shared_deadlines||[]).map(o=>({...o,shared:true})),...(t.private_deadlines||[]).map(o=>({...o,shared:false}))].sort((a,b)=>a.deadline.localeCompare(b.deadline)).map(o=>`<button ${o.shared?`data-deadline-space="${o.space_id}"`:`data-app="${o.id}"`} class="w-full text-left flex flex-wrap items-center gap-3 py-3 border-t border-stone-100 hover:bg-stone-50 transition-colors"><div class="flex-1 min-w-32"><div class="text-[15px] font-semibold">${esc(o.title)}</div><div class="text-[13px] text-stone-500 mt-1">${esc(o.company||'')} · ${fmtDate(o.deadline)}</div></div>${privacyChip(o.space_label)}${deadlineChip(o.deadline)}</button>`).join('') || '<p class="text-sm text-stone-400 py-3">No deadlines to flag. Add dates to your shared links or private applications.</p>'}
      </div>
    </section>
    ${actions ? `<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start"><div class="lg:col-span-2 min-w-0">${taskSections}</div>
      <div class="min-w-0"><h2 class="text-xs font-bold text-brand-600 uppercase tracking-widest mb-2 mt-1">Application next actions</h2><div class="stagger">${t.application_actions.map(appAction).join('')}</div></div></div>`
      : taskSections}
  </div>`;
  main().querySelectorAll('[data-done]').forEach(b => b.onclick = async e => {
    e.stopPropagation();
    const card = b.closest('[data-item]');
    const isDone = b.classList.contains('bg-emerald-500');
    await api('/items/' + b.dataset.done, { method: 'PATCH', body: { status: isDone ? 'open' : 'done' } });
    renderToday();
  });
  main().querySelectorAll('[data-item]').forEach(c => c.onclick = () => openItemDetail(c.dataset.item, renderToday));
  main().querySelectorAll('[data-app]').forEach(c => c.onclick = () => openAppDetail(c.dataset.app, renderToday));
  main().querySelectorAll('[data-deadline-space]').forEach(b=>b.onclick=()=>go('space',b.dataset.deadlineSpace));
  document.getElementById('quickadd').onclick = () => { go('my'); view.tab = 'todos'; };
}

/* ---------- item detail modal ---------- */
async function openItemDetail(itemId, refresh) {
  let audit = [];
  try { audit = await api('/audit/items/' + itemId); } catch (e) {}
  const last = audit[0];
  const auditLine = last
    ? `${last.action === 'create' ? 'Created' : 'Updated'} by ${last.actor_type === 'agent' ? 'Instinct' : 'you'}, ${fmtDateTime(last.created_at)}`
    : '';
  const items = view._items || [];
  const item = items.find(x => x.id === itemId) || (await fetchItem(itemId));
  if (!item) return;
  const m = openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-4">
        ${statusChip(item.status)}
        <button data-close class="text-stone-400 hover:text-stone-700">${icon('x','w-5 h-5')}</button>
      </div>
      <form id="itf" class="space-y-4">
        <input id="it_title" class="input !text-base font-semibold" value="${esc(item.title)}" required>
        <div><label class="label">Notes</label>
          <textarea id="it_desc" rows="3" class="input" placeholder="Add a note...">${esc(item.description || '')}</textarea></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">Status</label>
            <select id="it_status" class="input">${Object.entries(STATUS_LABEL).map(([k,l]) => `<option value="${k}" ${k===item.status?'selected':''}>${l}</option>`).join('')}</select></div>
          <div><label class="label">Due date</label>
            <input id="it_due" type="date" class="input" value="${item.due_date || ''}"></div>
        </div>
        <div class="flex items-center justify-between pt-1">
          <button type="button" id="it_del" class="btn-danger">${icon('trash','w-4 h-4')} Delete</button>
          <button class="btn-primary">Save changes</button>
        </div>
      </form>
      ${auditLine ? `<div class="mt-5 pt-4 border-t border-stone-100 text-xs text-stone-400 flex items-center gap-1.5">${icon('clock','w-3.5 h-3.5')} ${esc(auditLine)}</div>` : ''}
    </div>`);
  m.querySelector('#itf').onsubmit = async e => {
    e.preventDefault();
    await api('/items/' + itemId, { method: 'PATCH', body: {
      title: m.querySelector('#it_title').value,
      description: m.querySelector('#it_desc').value || null,
      status: m.querySelector('#it_status').value,
      due_date: m.querySelector('#it_due').value || null,
    }});
    closeModal(); toast('Saved'); refresh();
  };
  m.querySelector('#it_del').onclick = async () => {
    closeModal();
    if (await confirmDlg({ title: 'Delete this item?', body: 'This removes it for everyone who can see this space.' })) {
      await api('/items/' + itemId, { method: 'DELETE' }); toast('Deleted'); refresh();
    }
  };
}
async function fetchItem(id) {
  // no direct GET /items/:id; search the spaces we can see
  for (const s of spaces) {
    try { const its = await api(`/spaces/${s.id}/items`); const f = its.find(x => x.id === id); if (f) return f; } catch (e) {}
  }
  return null;
}

/* ---------- application detail modal ---------- */
async function openAppDetail(appId, refresh) {
  const apps = await api('/applications');
  const a = apps.find(x => x.id === appId);
  if (!a) return;
  let audit = [];
  try { audit = await api('/audit/applications/' + appId); } catch (e) {}
  const last = audit[0];
  const auditLine = last ? `${last.action === 'create' ? 'Created' : 'Updated'} by ${last.actor_type === 'agent' ? 'Instinct' : 'you'}, ${fmtDateTime(last.created_at)}` : '';
  const m = openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-4">
        ${appStatusChip(a.status)} ${privacyChip('Private')}
        <button data-close class="text-stone-400 hover:text-stone-700">${icon('x','w-5 h-5')}</button>
      </div>
      <form id="apf" class="space-y-4">
        <input id="ap_title" class="input !text-base font-semibold" value="${esc(a.title)}" required>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">Company</label><input id="ap_company" class="input" value="${esc(a.company || '')}"></div>
          <div><label class="label">Status</label>
            <select id="ap_status" class="input">${APP_STATUSES.map(s => `<option value="${s}" ${s===a.status?'selected':''}>${APP_STATUS_LABEL[s]}</option>`).join('')}</select></div>
          <div><label class="label">Link</label><input id="ap_url" class="input" value="${esc(a.url || '')}" placeholder="https://..."></div>
          <div><label class="label">Deadline</label><input id="ap_deadline" type="date" class="input" value="${a.deadline || ''}"></div>
          <div><label class="label">Resume version</label><input id="ap_resume" class="input" value="${esc(a.resume_version || '')}" placeholder="e.g. v3-swe"></div>
          <div><label class="label">Next action</label><input id="ap_next" class="input" value="${esc(a.next_action || '')}" placeholder="e.g. Follow up"></div>
        </div>
        <div><label class="label">Notes <span class="font-normal text-stone-400">- only you can see this</span></label>
          <textarea id="ap_notes" rows="3" class="input">${esc(a.notes || '')}</textarea></div>
        <div class="flex items-center justify-between pt-1">
          <button type="button" id="ap_del" class="btn-danger">${icon('trash','w-4 h-4')} Delete</button>
          <button class="btn-primary">Save changes</button>
        </div>
      </form>
      ${auditLine ? `<div class="mt-5 pt-4 border-t border-stone-100 text-xs text-stone-400 flex items-center gap-1.5">${icon('clock','w-3.5 h-3.5')} ${esc(auditLine)}</div>` : ''}
    </div>`, true);
  m.querySelector('#apf').onsubmit = async e => {
    e.preventDefault();
    const g = id => m.querySelector('#' + id).value || null;
    await api('/applications/' + appId, { method: 'PATCH', body: {
      title: m.querySelector('#ap_title').value, company: g('ap_company'), url: g('ap_url'),
      status: m.querySelector('#ap_status').value, deadline: g('ap_deadline'),
      resume_version: g('ap_resume'), next_action: g('ap_next'), notes: g('ap_notes'),
    }});
    closeModal(); toast('Saved'); refresh();
  };
  m.querySelector('#ap_del').onclick = async () => {
    closeModal();
    if (await confirmDlg({ title: 'Delete this application?', body: 'Your notes and tracking for this application are removed.' })) {
      await api('/applications/' + appId, { method: 'DELETE' }); toast('Deleted'); refresh();
    }
  };
}

/* ---------- My Space ---------- */
function tabBar(tabs, active) {
  return `<div class="flex w-fit max-w-full flex-nowrap overflow-x-auto gap-1 p-1 bg-stone-200/60 rounded-xl mb-6">${tabs.map(([k, l]) =>
    `<button data-tab="${k}" class="tabbtn shrink-0 !px-2 md:!px-3.5 !text-xs md:!text-sm ${k === active ? 'active' : ''}">${l}</button>`).join('')}</div>`;
}

async function renderMySpace(tab) {
  view.tab = tab;
  const personal = spaces.find(s => s.type === 'personal');
  if (!personal) { main().innerHTML = 'No personal space found.'; return; }
  const tabs = [['todos','Todos'],['plans','Plans'],['projects','Projects'],['apps','Applications']];
  main().innerHTML = `
  <div class="view-in">
    <div class="flex items-center gap-3 mb-1">
      <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight">My Space</h1>
      ${privacyChip('Private')}
    </div>
    <p class="text-sm text-stone-500 mb-5">Only you can see what is in here.</p>
    ${tabBar(tabs, tab)}
    <div id="tabbody"></div>
  </div>`;
  main().querySelectorAll('[data-tab]').forEach(b => b.onclick = () => renderMySpace(b.dataset.tab));
  const body = document.getElementById('tabbody');

  if (tab === 'todos') return myTodos(body, personal);
  if (tab === 'plans' || tab === 'projects') return myCollections(body, personal, tab);
  if (tab === 'apps') return myApps(body);
}

async function myTodos(body, personal) {
  const items = await api(`/spaces/${personal.id}/items`);
  view._items = items;
  const todos = items.filter(i => i.type === 'todo' && i.status !== 'archived');
  const today = new Date(); today.setHours(0,0,0,0);
  const groups = { overdue: [], today: [], upcoming: [], nodate: [], done: [] };
  todos.forEach(i => {
    if (i.status === 'done') return groups.done.push(i);
    if (!i.due_date) return groups.nodate.push(i);
    const d = new Date(i.due_date + 'T00:00:00');
    if (d < today) groups.overdue.push(i); else if (+d === +today) groups.today.push(i); else groups.upcoming.push(i);
  });
  const row = i => `
    <div class="card p-3 mb-2 flex items-center gap-3 cursor-grab hover:shadow-pop transition-shadow" draggable="true" data-drag="${i.id}" data-item="${i.id}">
      <button data-done="${i.id}" class="w-5 h-5 rounded-full border-2 ${i.status==='done' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-stone-300 hover:border-emerald-500 text-transparent'} flex items-center justify-center shrink-0 transition-colors">${icon('check','w-3 h-3')}</button>
      <div class="flex-1 min-w-0"><div class="font-medium text-[15px] truncate ${i.status==='done' ? 'line-through text-stone-400' : ''}">${esc(i.title)}</div></div>
      ${i.due_date ? `<span class="chip chip-stone">${icon('cal','w-3 h-3')} ${fmtDate(i.due_date)}</span>` : ''}
    </div>`;
  const section = (label, list, cls) => list.length ?
    `<h3 class="text-xs font-bold uppercase tracking-wide ${cls} mt-5 mb-2">${label}</h3><div data-zone>${list.map(row).join('')}</div>` : '';
  body.innerHTML = `
    <form id="add" class="card p-2 flex flex-wrap sm:flex-nowrap gap-2 mb-2">
      <input id="t" required placeholder="Quick add a todo..." class="input !ring-0 !w-auto flex-1 min-w-40">
      <input id="d" type="date" class="input !ring-0 !w-auto sm:!w-40">
      <button class="btn-primary">${icon('plus','w-4 h-4')} Add</button>
    </form>
    <div id="list">
      ${section('Overdue', groups.overdue, 'text-red-500')}
      ${section('Today', groups.today, 'text-amber-500')}
      ${section('Upcoming', groups.upcoming, 'text-stone-400')}
      ${section('No date', groups.nodate, 'text-stone-400')}
      ${section('Done', groups.done, 'text-emerald-500')}
      ${!todos.length ? `<div class="rounded-xl border-2 border-dashed border-stone-200 p-8 text-center mt-4">
        <div class="text-stone-300 flex justify-center mb-2">${icon('inbox','w-8 h-8')}</div>
        <p class="text-sm text-stone-400">No todos yet. Add your first one above.</p></div>` : ''}
    </div>`;
  document.getElementById('add').onsubmit = async e => {
    e.preventDefault();
    await api(`/spaces/${personal.id}/items`, { method: 'POST',
      body: { type: 'todo', title: document.getElementById('t').value, due_date: document.getElementById('d').value || null } });
    renderMySpace('todos');
  };
  bindRows(body, () => renderMySpace('todos'));
  enableDrag(body, todos);
}

function bindRows(scope, refresh) {
  scope.querySelectorAll('[data-done]').forEach(b => b.onclick = async e => {
    e.stopPropagation();
    const done = b.classList.contains('bg-emerald-500');
    await api('/items/' + b.dataset.done, { method: 'PATCH', body: { status: done ? 'open' : 'done' } });
    refresh();
  });
  scope.querySelectorAll('[data-item]').forEach(c => c.onclick = () => openItemDetail(c.dataset.item, refresh));
}

function enableDrag(scope, todos) {
  let dragId = null;
  scope.querySelectorAll('[data-drag]').forEach(card => {
    card.addEventListener('dragstart', () => { dragId = card.dataset.drag; card.classList.add('dragging'); });
    card.addEventListener('dragend', () => card.classList.remove('dragging'));
    card.addEventListener('dragover', e => { e.preventDefault(); card.classList.add('drag-over'); });
    card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
    card.addEventListener('drop', async e => {
      e.preventDefault(); card.classList.remove('drag-over');
      if (!dragId || dragId === card.dataset.drag) return;
      const target = todos.find(t => t.id === card.dataset.drag);
      if (!target) return;
      await api('/items/' + dragId, { method: 'PATCH', body: {
        sort_order: (target.sort_order || 0) + 1, due_date: target.due_date } });
      toast('Moved');
      renderMySpace('todos');
    });
  });
}

async function myCollections(body, personal, tab) {
  const kind = tab === 'plans' ? 'plan' : 'project';
  const items = await api(`/spaces/${personal.id}/items`);
  view._items = items;
  const parents = items.filter(i => i.type === kind && i.status !== 'archived');
  body.innerHTML = `
    <form id="add" class="card p-2 flex gap-2 mb-5">
      <input id="t" required placeholder="New ${kind}... e.g. ${kind === 'plan' ? 'Week of Nov 24' : 'Qyad'}" class="input !ring-0 !w-auto flex-1">
      <button class="btn-primary">${icon('plus','w-4 h-4')} Add</button>
    </form>
    <div class="grid gap-4 lg:grid-cols-2">
    ${parents.map(p => {
      const kids = items.filter(i => i.parent_id === p.id);
      const done = kids.filter(k => k.status === 'done').length;
      const pct = kids.length ? Math.round(done / kids.length * 100) : 0;
      return `<div class="card p-5">
        <div class="flex items-center gap-3 mb-3">
          <div class="font-semibold flex-1 truncate">${esc(p.title)}</div>
          <span class="text-xs font-semibold text-stone-400">${done}/${kids.length}</span>
        </div>
        <div class="h-1.5 rounded-full bg-stone-100 mb-4 overflow-hidden"><div class="h-full rounded-full ${pct === 100 ? 'bg-emerald-500' : 'bg-brand-500'} transition-all" style="width:${pct}%"></div></div>
        <div class="space-y-1">
        ${kids.map(k => `
          <div class="flex items-center gap-2.5 py-1.5 px-2 -mx-2 rounded-lg hover:bg-stone-50 cursor-pointer" data-item="${k.id}">
            <button data-done="${k.id}" class="w-[18px] h-[18px] rounded-full border-2 ${k.status==='done' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-stone-300 hover:border-emerald-500 text-transparent'} flex items-center justify-center shrink-0 transition-colors">${icon('check','w-2.5 h-2.5')}</button>
            <span class="text-sm ${k.status==='done' ? 'line-through text-stone-400' : ''}">${esc(k.title)}</span>
            ${k.due_date ? `<span class="ml-auto text-[11px] text-stone-400">${fmtDate(k.due_date)}</span>` : ''}
          </div>`).join('') || '<p class="text-xs text-stone-400 py-1">No tasks yet.</p>'}
        </div>
        <form data-addkid="${p.id}" class="flex gap-2 mt-3">
          <input required placeholder="Add task..." class="input !py-1.5 !text-[13px] !w-auto flex-1">
          <button class="btn-ghost !py-1.5 !px-2.5 text-xs">Add</button>
        </form>
      </div>`;
    }).join('')}
    </div>
    ${!parents.length ? `<div class="rounded-xl border-2 border-dashed border-stone-200 p-8 text-center">
      <div class="text-stone-300 flex justify-center mb-2">${icon('inbox','w-8 h-8')}</div>
      <p class="text-sm text-stone-400">No ${kind}s yet. ${kind === 'plan' ? 'Plans are dated collections, like a week.' : 'Projects hold their own tasks and progress.'}</p></div>` : ''}`;
  document.getElementById('add').onsubmit = async e => {
    e.preventDefault();
    await api(`/spaces/${personal.id}/items`, { method: 'POST', body: { type: kind, title: document.getElementById('t').value } });
    renderMySpace(tab);
  };
  body.querySelectorAll('[data-addkid]').forEach(f => f.onsubmit = async e => {
    e.preventDefault();
    await api(`/spaces/${personal.id}/items`, { method: 'POST',
      body: { type: 'todo', title: f.querySelector('input').value, parent_id: f.dataset.addkid } });
    renderMySpace(tab);
  });
  bindRows(body, () => renderMySpace(tab));
}

async function myApps(body) {
  const apps = await api('/applications');
  body.innerHTML = `
    <form id="add" class="card p-2 flex flex-wrap gap-2 mb-5">
      <input id="t" required placeholder="Role / title" class="input !ring-0 !w-auto flex-1 min-w-36">
      <input id="c" placeholder="Company" class="input !ring-0 !w-32">
      <input id="u" placeholder="Link" class="input !ring-0 !w-auto flex-1 min-w-36 hidden sm:block">
      <input id="d" type="date" class="input !ring-0 !w-36 hidden sm:block">
      <button class="btn-primary">${icon('plus','w-4 h-4')} Add</button>
    </form>
    <div class="table-scroll" role="region" aria-label="Private applications table" tabindex="0"><table class="opportunities-table private-apps-table"><thead><tr><th>Role</th><th>Company</th><th>Deadline</th><th>Next action</th><th>Status</th><th>Link</th></tr></thead><tbody>${apps.map(a=>`<tr><td class="role-cell"><button data-open-application="${a.id}" class="table-role">${esc(a.title)}</button><span class="table-meta">${esc(a.resume_version||'')}</span></td><td>${esc(a.company||'Not added')}</td><td class="date-cell">${a.deadline?esc(a.deadline):'<span class="table-muted">Not stated</span>'}</td><td>${esc(a.next_action||'—')}</td><td><select data-app-move="${a.id}" class="table-stage" aria-label="Stage for ${esc(a.title)}">${APP_STATUSES.map(st=>`<option value="${st}" ${a.status===st?'selected':''}>${APP_STATUS_LABEL[st]}</option>`).join('')}</select></td><td>${a.url?`<a class="table-apply" target="_blank" rel="noopener noreferrer" href="${safeLink(a.url)}">Apply ↗</a>`:'—'}</td></tr>`).join('')}</tbody></table></div>${!apps.length?'<p class="table-empty">No private applications yet. Add one above or track a team link privately.</p>':''}`;
  document.getElementById('add').onsubmit = async e => {
    e.preventDefault();
    const g = id => { const el = document.getElementById(id); return el && el.value ? el.value : null; };
    await api('/applications', { method: 'POST', body: {
      title: document.getElementById('t').value, company: g('c'), url: g('u'), deadline: g('d') } });
    renderMySpace('apps');
  };
  body.querySelectorAll('[data-open-application]').forEach(c => c.onclick = () => openAppDetail(c.dataset.openApplication, () => renderMySpace('apps')));
  let moving=false;
  const move=async(id,status)=>{if(moving)return;const app=apps.find(a=>a.id===id);if(!app||app.status===status)return;moving=true;
    try{await api('/applications/'+id,{method:'PATCH',body:{status}});toast('Moved to '+APP_STATUS_LABEL[status]);await renderMySpace('apps');}catch(e){toast('Move not saved: '+e.message,'err');body.querySelector('[data-app-move="'+id+'"]').value=app.status;}finally{moving=false;}};
  body.querySelectorAll('[data-app-move]').forEach(el=>el.onchange=()=>move(el.dataset.appMove,el.value));


}

/* ---------- Group / College space ---------- */
async function renderSpace(spaceId, tab) {
  const space = await api('/spaces/' + spaceId);
  view.arg = spaceId;
  const isOwner = space.role === 'owner';
  const isCollege = space.type === 'college';
  const tabs = [['opportunities', isCollege ? 'Resources' : 'Opportunities'], ['updates','Updates'], ['projects','Projects'], ['members','Members']];
  const memberStack = space.members.slice(0, 4).map(m => avatar(m.user.name, 'w-7 h-7 text-[10px] ring-2 ring-white -ml-2 first:ml-0')).join('');
  main().innerHTML = `
  <div class="view-in">
    <div class="flex flex-wrap items-center gap-3 mb-1">
      <span class="w-10 h-10 rounded-xl ${isCollege ? 'bg-violet-100 text-violet-600' : 'bg-sky-100 text-sky-600'} flex items-center justify-center">${icon(isCollege ? 'cap' : 'users','w-5 h-5')}</span>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap"><h1 class="text-xl sm:text-2xl font-extrabold tracking-tight truncate">${esc(space.name)}</h1><span class="hidden sm:inline">${privacyChip(isCollege ? 'College' : space.name)}</span></div>
        <p class="text-xs text-stone-500 mt-0.5">${space.member_count} member(s) · visible to everyone in this space</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="hidden sm:flex">${memberStack}</div>
        ${isOwner ? `<button id="invbtn" class="btn-ghost !py-1.5">${icon('link','w-4 h-4')} Invite</button>` : ''}
      </div>
    </div>
    <div class="mt-4">${tabBar(tabs, tab)}</div>
    <div id="tabbody"></div>
  </div>`;
  main().querySelectorAll('[data-tab]').forEach(b => b.onclick = () => renderSpace(spaceId, b.dataset.tab));
  const inv = document.getElementById('invbtn');
  if (inv) inv.onclick = () => openInvite(space);
  const body = document.getElementById('tabbody');
  if (tab === 'opportunities') return spaceOpps(body, space);
  if (tab === 'updates') return spaceUpdates(body, space);
  if (tab === 'projects') return spaceProjects(body, space);
  if (tab === 'members') return spaceMembers(body, space);
}

function openInvite(space) {
  const m = openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-1">
        <h3 class="font-bold text-lg">Invite friends</h3>
        <button data-close class="text-stone-400 hover:text-stone-700">${icon('x','w-5 h-5')}</button>
      </div>
      <p class="text-sm text-stone-500 mb-5">Anyone with the link can join <b>${esc(space.name)}</b>. Links expire after 14 days.</p>
      ${['localhost','127.0.0.1'].includes(location.hostname)?'<p class="text-xs text-amber-700 bg-amber-50 rounded-lg p-3 mb-4">You are running locally. This invite works only on this computer. For friends on other devices, deploy the app with a persistent database and HTTPS first.</p>':''}
      <button id="mk" class="btn-primary w-full">${icon('link','w-4 h-4')} Create invite link</button>
      <div id="out" class="hidden mt-4">
        <label class="label">Share this link</label>
        <div class="flex gap-2">
          <input id="lnk" readonly class="input !text-xs font-mono" onclick="this.select()">
          <button id="cp" class="btn-ghost shrink-0">${icon('copy','w-4 h-4')}</button>
        </div>
      </div>
    </div>`);
  m.querySelector('#mk').onclick = async e => {
    e.preventDefault();
    const r = await api(`/spaces/${space.id}/invites`, { method: 'POST' });
    const url = location.origin + r.join_path;
    m.querySelector('#out').classList.remove('hidden');
    m.querySelector('#lnk').value = url;
    m.querySelector('#mk').textContent = 'Create another link';
  };
  m.querySelector('#cp').onclick = async () => {
    const url = m.querySelector('#lnk').value;
    try { await navigator.clipboard.writeText(url); }
    catch (e) { m.querySelector('#lnk').select(); document.execCommand('copy'); }
    toast('Link copied');
  };
}

/* Shared opportunity inbox: data stays in the space, private tracking stays private. */
const OPP_RESPONSE_LABEL = {interested:'Interested', applied:'Applied', skipped:'Skipped'};
const oppFilters = {};

function deadlineInfo(value) {
  if (!value) return {text:'No deadline', cls:'chip-stone', days:null};
  const today = new Date().toLocaleDateString('en-CA', {timeZone:me.timezone || 'Asia/Kolkata'});
  const days = Math.round((Date.parse(value+'T00:00:00Z') - Date.parse(today+'T00:00:00Z'))/86400000);
  return {days, text:days < 0 ? `${-days}d overdue` : days === 0 ? 'Closes today' : days === 1 ? '1 day left' : `${days} days left`,
    cls:days < 0 ? 'chip-red' : days <= 2 ? 'chip-private' : days <= 7 ? 'chip-blue' : 'chip-stone'};
}
function deadlineChip(value) {const d=deadlineInfo(value);return `<span class="chip ${d.cls}">${icon('clock','w-3 h-3')}${d.text}</span>`;}
function safeLink(value) {try {const u=new URL(value);return ['http:','https:'].includes(u.protocol)?esc(u.href):'#';}catch(e){return '#';}}
function responseSelect(o) {return `<label class="block"><span class="sr-only">My shared status for ${esc(o.title)}</span><select data-response="${o.id}" class="input !text-xs !py-1.5 !w-32" aria-label="My shared status for ${esc(o.title)}"><option value="">Not shared</option>${Object.entries(OPP_RESPONSE_LABEL).map(([v,l])=>`<option value="${v}" ${o.my_shared_status===v?'selected':''}>${l}</option>`).join('')}</select></label>`;}
function peopleResponses(o) {return o.responses.length ? o.responses.map(r=>`<div class="flex items-center gap-1.5 text-xs py-0.5">${avatar(r.name,'w-5 h-5 text-[8px]')}<span>${esc(r.name)}</span><span class="text-stone-400">${OPP_RESPONSE_LABEL[r.status]}</span></div>`).join('') : '<span class="text-xs text-stone-400">No shared updates yet</span>';}
function trackButton(o) {return `<button data-track="${o.id}" class="btn-ghost !text-xs !py-1.5 whitespace-nowrap">${icon('lock','w-3 h-3')}${o.tracked_by_me?'Open private':'Save privately'}</button>`;}

async function spaceOpps(body, space) {
  const [saved, profile, catalog] = await Promise.all([api(`/spaces/${space.id}/opportunities`),api('/match-profile'),api('/opportunity-catalog')]);
  const urls=new Set(saved.map(o=>o.url));
  const suggestions=catalog.jobs.filter(j=>!urls.has(j.url)).map(j=>({...j,id:'catalog:'+j.id,catalog_id:j.id,suggested:true,responses:[],my_shared_status:null,tracked_by_me:false,updated_at:j.created_at}));
  const opps=[...saved,...suggestions];
  for (const o of opps) {
    const text = [o.title,o.company,o.description].join(' ').toLowerCase();
    const tokens = new Set((text.match(/[a-z0-9][a-z0-9.+#-]*|\.net/g)||[]).map(t=>t.replace(/[.-]+$/,'')));
    o.matched_terms = profile.terms.filter(t=>t.includes(' ')?text.includes(t):tokens.has(t));
    const loc=(o.description||'').match(/Location: ([^.]+)\./);o.location=o.location||(loc?loc[1]:'');
    o.display_description=(o.description||'').replace(/^Source: [^\n]+\nLocation: [^.]+\. /,'').replace(/\nVerify current status[\s\S]*/,'');
    o.match_count = o.matched_terms.length;
    if(o.match_score===undefined){o.match_score=null;o.score_method='Set your private match profile to see weighted coverage.';}
  }
  const f = oppFilters[space.id] || (oppFilters[space.id]={q:'',kind:'',due:'',status:'',sort:'deadline',dir:1,recency:'',layout:'auto',matches:''});
  body.innerHTML = `
    <section class="hero-panel rounded-2xl text-stone-900 p-5 sm:p-6 mb-5 relative overflow-hidden">
      <div class="hero-fx"><span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span></div>
      <div class="flex flex-wrap items-start justify-between gap-3"><div><div class="text-[11px] font-bold tracking-[.14em] text-brand-600 uppercase mb-2">Your team's link inbox</div>
      <h2 class="text-xl font-bold tracking-tight">Good links. No lost deadlines.</h2><p class="text-xs sm:text-sm hero-sub mt-1">Drop links here. Decide together. Track privately.</p></div>
      <span class="chip bg-white/80 text-brand-700 ring-1 ring-brand-200 shadow-sm">${saved.length} saved · ${suggestions.length} suggested</span></div>
      <form id="link-capture" class="flex flex-wrap gap-2 mt-5"><label class="flex-1 min-w-0 basis-full sm:basis-0"><span class="sr-only">Paste opportunity link</span><input id="capture-url" class="input !bg-white/90 !text-stone-900 !ring-1 !ring-brand-200 focus:!ring-2 focus:!ring-brand-500 shadow-sm" placeholder="Paste a job, internship or event link..." required></label><button class="btn-primary">${icon('plus','w-4 h-4')} Save link</button><button type="button" id="new-opp" class="btn !bg-white/80 !text-stone-700 !ring-1 !ring-stone-200 hover:!bg-white shadow-sm">Add details</button></form>
      <div id="capture-error" role="alert" class="text-sm text-red-600 font-medium mt-2 hidden"></div>
      <p class="hidden sm:block text-xs hero-note mt-3">Paste a checked shortlist link to fill details. Other links open a review form before saving.</p>
    </section>
    <div class="filter-workbench"><div class="filter-top"><label class="block flex-1 min-w-0"><span class="sr-only">Search opportunities</span><input id="opp-search" class="input" placeholder="Search title, company, link, notes..." value="${esc(f.q)}"></label>
    <details class="opp-controls"><summary class="filter-trigger">${icon('flag','w-4 h-4')} Filters <span id="filter-badge" class="filter-badge hidden"></span></summary><div class="filter-panel">
      <div class="filter-panel-title">Refine your links <button type="button" id="filter-close" class="icon-button" aria-label="Close filters">${icon('x','w-4 h-4')}</button></div>
      <select id="opp-kind" class="input !w-auto" aria-label="Filter by type"><option value="">All types</option>${['internship','job','event','other'].map(k=>`<option ${f.kind===k?'selected':''}>${k}</option>`).join('')}</select>
      <select id="opp-due" class="input !w-auto" aria-label="Filter by deadline">${[['','Any deadline'],['week','Due in 7 days'],['overdue','Overdue'],['none','Missing deadline']].map(([v,l])=>`<option value="${v}" ${f.due===v?'selected':''}>${l}</option>`).join('')}</select>
      <select id="opp-status" class="input !w-auto" aria-label="Filter my shared status">${[['','All my statuses'],['unshared','Not shared'],...Object.entries(OPP_RESPONSE_LABEL)].map(([v,l])=>`<option value="${v}" ${f.status===v?'selected':''}>${l}</option>`).join('')}</select>
      <select id="opp-recency" class="input !w-auto" aria-label="Filter by recent activity">${[['','All activity'],['posted','Posted in last 7 days'],['updated','Updated in last 7 days']].map(([v,l])=>`<option value="${v}" ${f.recency===v?'selected':''}>${l}</option>`).join('')}</select>
      <select id="opp-matches" class="input !w-auto" aria-label="Filter keyword matches"><option value="">All keyword matches</option><option value="yes" ${f.matches?'selected':''}>Matches me</option></select><button id="match-settings" class="btn-ghost">Match profile</button>
      <button id="opp-refresh" class="btn-ghost" aria-label="Refresh table">Refresh</button>
    </div></details></div><div class="quick-filters" role="group" aria-label="Quick filters"><button data-quick="all" class="quick-chip">All links</button><button data-quick="internship" class="quick-chip">Internships</button><button data-quick="week" class="quick-chip">Due this week</button><button data-quick="matches" class="quick-chip">Matches me</button><div class="flex-1"></div><button id="opp-reset" class="text-xs text-stone-500">Reset filters</button></div><div id="active-filters" class="active-filters"></div></div>
    <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500 mb-3"><span id="opp-count"></span><div class="flex items-center gap-2"><label for="opp-sort">Sort</label><select id="opp-sort" class="bg-transparent text-stone-700 font-medium">${[['deadline','Deadline'],['title','Title'],['company','Company'],['created_at','Recently posted'],['updated_at','Recently updated'],['match_count','Keyword matches']].map(([v,l])=>`<option value="${v}" ${f.sort===v?'selected':''}>${l}</option>`).join('')}</select><button id="opp-dir" class="px-2 py-1 rounded border border-stone-200" aria-label="Reverse sort">${f.dir===1?'↑':'↓'}</button></div></div>
    <p class="catalog-inline-note">Includes a dated shortlist checked 23 Nov 2026. Suggested links are not saved to your team until you choose Add to list. Confirm status on the source. Known past dates are hidden; old checks are marked for recheck.</p><div id="opp-results"></div>
    <p class="text-xs leading-5 text-stone-400 mt-4">Everyone in this space can edit shared details. Your status is shared only when you choose it. Private notes, resume and tracker status never appear here. Use Refresh to see friends' latest changes. Dates use your profile timezone (${esc(me.timezone)}).</p>`;
  const draw = () => {
    let rows=opps.filter(o=>{
      const d=deadlineInfo(o.deadline).days;
      return (!f.q || [o.title,o.company,o.url,o.description].some(v=>(v||'').toLowerCase().includes(f.q.toLowerCase()))) &&
        (!f.matches || o.match_count>0) && (!f.recency || Date.now()-Date.parse(f.recency==='posted'?o.created_at+'Z':o.updated_at)<=7*86400000) && (!f.kind||o.kind===f.kind) && (!f.status || (f.status==='unshared'?!o.my_shared_status:o.my_shared_status===f.status)) &&
        (!f.due || (f.due==='week'&&d!==null&&d>=0&&d<=7)||(f.due==='overdue'&&d!==null&&d<0)||(f.due==='none'&&d===null));
    });
    rows.sort((a,b)=>{
      if(f.sort==='match_count') return (b.match_count-a.match_count)*f.dir;
      if(f.sort==='deadline' && (!a.deadline||!b.deadline))return !a.deadline&&!b.deadline?0:!a.deadline?1:-1;
      const n=String(a[f.sort]||'').localeCompare(String(b[f.sort]||''));return n*f.dir*(['created_at','updated_at'].includes(f.sort)?-1:1);
    });
    const keys=['q','kind','due','status','recency','matches'];const active=keys.filter(k=>f[k]);
    const labels={q:'Search',kind:'Type',due:'Deadline',status:'Status',recency:'Activity',matches:'Keyword match'};
    body.querySelector('#active-filters').innerHTML=active.map(k=>`<button class="active-filter" data-remove-filter="${k}">${labels[k]}: ${esc(k==='q'?f[k]:(body.querySelector('#'+({kind:'opp-kind',due:'opp-due',status:'opp-status',recency:'opp-recency',matches:'opp-matches'}[k]))?.selectedOptions[0]?.textContent||f[k]))} ${icon('x','w-3 h-3')}</button>`).join('');
    body.querySelector('#filter-badge').textContent=active.length;body.querySelector('#filter-badge').classList.toggle('hidden',!active.length);
    body.querySelector('#opp-reset').hidden=!active.length;
    body.querySelectorAll('[data-quick]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.quick==='all'?!active.length:b.dataset.quick==='internship'?f.kind==='internship':b.dataset.quick==='week'?f.due==='week':!!f.matches)));
    body.querySelectorAll('[data-remove-filter]').forEach(b=>b.onclick=()=>{f[b.dataset.removeFilter]='';syncFilters();draw();});
    body.querySelector('#opp-count').textContent=`${rows.length} of ${opps.length} links · ${saved.length} saved, ${suggestions.length} suggested`;
    const th=(k,l)=>`<th class="px-4 py-3 text-left"><button data-sort="${k}" class="font-semibold">${l} ${f.sort===k?(f.dir===1?'↑':'↓'):''}</button></th>`;
    body.querySelector('#opp-results').innerHTML=rows.length ? `<div class="table-scroll" role="region" aria-label="Opportunities table, scroll horizontally for all columns" tabindex="0"><table class="opportunities-table"><caption class="sr-only">All opportunities, one link per row</caption><thead><tr>${th('title','Role / opportunity')}${th('company','Company / location')}<th>Type</th>${th('deadline','Deadline')}${th('match_count','Match')}<th>Status</th><th>Link</th></tr></thead><tbody>${rows.map(o=>{
      let host='';try{host=new URL(o.url).hostname;}catch(e){}
      const incomplete=!o.title||o.title===host||o.title==='www.'+host;
      return `<tr><td class="role-cell">${o.suggested?'<span class="suggestion-label">Suggested</span>':''}<button ${o.suggested?'':`data-edit="${o.id}"`} class="table-role">${esc(incomplete?'Details needed':o.title)}</button><details class="table-details"><summary>Details</summary><p>${esc(incomplete?'Open the source and add its real role and company.':o.display_description||o.description||'No notes added.')}</p>${profile.terms.length?`<p>${esc(o.score_method)} Matched: ${esc(o.matched_terms.join(', ')||'None')}. Skills weight 3; other terms 1.</p>`:''}<div class="table-detail-actions">${o.suggested?`<button data-catalog-team="${o.catalog_id}" class="btn-ghost">Add to team</button><button data-catalog-private="${o.catalog_id}" class="btn-ghost">Track privately</button><p>Checked ${esc(o.checked_at)}${o.stale?' · Needs recheck':''}. ${esc(o.verification)}.</p>`:`${trackButton(o)}<button data-edit="${o.id}" class="btn-ghost">Edit</button>${peopleResponses(o)}`}</div></details></td><td><span class="table-company">${esc(o.company||'Not added')}</span><span class="table-meta">${esc(o.location||'Location not added')}</span></td><td class="type-cell">${esc(o.kind==='event'?'Hackathon / event':o.kind)}</td><td class="date-cell">${o.deadline?esc(o.deadline):'<span class="table-muted">Not stated</span>'}</td><td class="match-cell">${profile.terms.length?`<span title="${esc(o.score_method)}">${o.match_score==null?'—':o.match_score+'%'}</span>`:'<span class="table-muted">—</span>'}</td><td>${o.suggested?'<span class="table-muted">Not saved</span>':responseSelect(o)}</td><td class="link-cell">${o.url?`<a class="table-apply" target="_blank" rel="noopener noreferrer" href="${safeLink(o.url)}">${o.kind==='event'?'Open':'Apply'} ↗</a>`:'<span class="table-muted">No link</span>'}</td></tr>`;
    }).join('')}</tbody></table></div><p class="table-phone-hint">Swipe the table sideways for Status and Apply. One row per link.</p>` : `<div class="table-empty"><p>${opps.length?'No matching links':'No links yet'}</p><button id="clear-filters" class="btn-ghost">Clear filters</button></div>`;
    for(const target of ['team','private'])body.querySelectorAll('[data-catalog-'+target+']').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/opportunity-catalog/'+b.getAttribute('data-catalog-'+target)+'/save',{method:'POST',body:target==='team'?{space_id:space.id}:{}});toast(target==='team'?'Saved to your team list':'Saved privately');await spaceOpps(body,space);}catch(e){toast(e.message,'err');}finally{b.disabled=false;}});
    body.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>openOppEditor(space,opps.find(o=>o.id===b.dataset.edit),()=>spaceOpps(body,space)));
    body.querySelectorAll('[data-sort]').forEach(b=>b.onclick=()=>{f.dir=f.sort===b.dataset.sort?-f.dir:1;f.sort=b.dataset.sort;spaceOpps(body,space);});
    body.querySelectorAll('[data-response]').forEach(el=>el.onchange=async()=>{
      try {await api(`/opportunities/${el.dataset.response}/my-response`,{method:'PUT',body:{status:el.value||null}});toast(el.value?'Status shared with this space':'Shared status cleared');await spaceOpps(body,space);}catch(e){toast(e.message,'err');await spaceOpps(body,space);}
    });
    body.querySelectorAll('[data-track]').forEach(b=>b.onclick=async()=>{
      try {const r=await api(`/opportunities/${b.dataset.track}/track`,{method:'POST'});toast('Only you can see this application');openAppDetail(r.id,()=>spaceOpps(body,space));await spaceOpps(body,space);}catch(e){toast(e.message,'err');}
    });
    const clear=body.querySelector('#clear-filters');if(clear)clear.onclick=()=>{Object.assign(f,{q:'',kind:'',due:'',status:'',recency:'',matches:''});spaceOpps(body,space);};
  };
  function syncFilters(){for(const [id,key] of [['opp-search','q'],['opp-kind','kind'],['opp-due','due'],['opp-status','status'],['opp-recency','recency'],['opp-matches','matches']])body.querySelector('#'+id).value=f[key];}
  body.querySelectorAll('.filter-panel select').forEach(el=>{const label=document.createElement('label');label.className='filter-field';const text=document.createElement('span');text.className='filter-field-label';text.textContent=el.getAttribute('aria-label').replace('Filter by ','').replace('Filter my ','My ').replace('Filter ','');el.before(label);label.append(text,el);});
  body.querySelector('#opp-reset').onclick=()=>{for(const k of ['q','kind','due','status','recency','matches'])f[k]='';syncFilters();draw();};
  body.querySelector('#filter-close').onclick=()=>body.querySelector('.opp-controls').open=false;
  body.querySelectorAll('[data-quick]').forEach(b=>b.onclick=()=>{const k=b.dataset.quick;if(k==='all')for(const x of ['q','kind','due','status','recency','matches'])f[x]='';else {const key={internship:'kind',week:'due',matches:'matches'}[k],val={internship:'internship',week:'week',matches:'yes'}[k];f[key]=f[key]===val?'':val;}syncFilters();draw();});
  draw();
  body.querySelector('#opp-search').oninput=e=>{f.q=e.target.value;draw();};
  for(const [id,key] of [['opp-kind','kind'],['opp-due','due'],['opp-status','status'],['opp-sort','sort'],['opp-recency','recency'],['opp-matches','matches']])body.querySelector('#'+id).onchange=e=>{f[key]=e.target.value;draw();};
  body.querySelector('#opp-dir').onclick=()=>{f.dir=-f.dir;body.querySelector('#opp-dir').textContent=f.dir===1?'↑':'↓';draw();};
  body.querySelector('#match-settings').onclick=()=>go('settings');
  body.querySelector('#opp-refresh').onclick=()=>spaceOpps(body,space);
  body.querySelector('#new-opp').onclick=()=>openOppEditor(space,null,()=>spaceOpps(body,space));
  body.querySelector('#link-capture').onsubmit=async e=>{
    e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;
    try {const preview=await api('/opportunity-preview',{method:'POST',body:{url:body.querySelector('#capture-url').value}});openOppEditor(space,null,()=>spaceOpps(body,space),preview);}
    catch(err){const msg=body.querySelector('#capture-error');msg.textContent=err.message;msg.classList.remove('hidden');}finally{button.disabled=false;}
  };
}

function openOppEditor(space, o, refresh, preview=null) {
  const draft=o||preview||{};
  const m=openModal(`<div class="p-6"><div class="flex justify-between items-center mb-2"><h3 class="text-lg font-bold">${o?'Edit shared opportunity':'Add opportunity'}</h3><button data-close aria-label="Close">${icon('x','w-5 h-5')}</button></div><p class="text-xs text-sky-600 mb-5">Shared with everyone in ${esc(space.name)}. Keep personal notes in your private tracker.</p><form id="opp-editor" class="space-y-4"><div><label class="label" for="oe-title">Title</label><input id="oe-title" class="input" required value="${esc(draft.title||'')}" placeholder="e.g. Software Engineering Intern"></div><div class="grid grid-cols-2 gap-3"><div><label class="label" for="oe-company">Company / organizer</label><input id="oe-company" class="input" value="${esc(draft.company||'')}"></div><div><label class="label" for="oe-kind">Type</label><select id="oe-kind" class="input">${['internship','job','event','other'].map(k=>`<option ${draft.kind===k?'selected':''}>${k}</option>`).join('')}</select></div></div><div><label class="label" for="oe-url">Original link</label><input id="oe-url" class="input" value="${esc(draft.url||'')}" placeholder="https://..."></div><div><label class="label" for="oe-deadline">Deadline</label><input id="oe-deadline" type="date" class="input" value="${draft.deadline||''}"><p class="text-xs text-stone-400 mt-1">Check the original listing. Leave blank if unknown.</p></div><div><label class="label" for="oe-notes">Shared notes</label><textarea id="oe-notes" class="input" rows="3" placeholder="Eligibility, requirements, useful context...">${esc(draft.description||'')}</textarea></div><div id="oe-error" role="alert" class="text-sm text-red-600"></div><button class="btn-primary w-full">${o?'Save shared changes':'Add to shared table'}</button></form>${o?'<p class="text-xs text-stone-400 mt-4">Changes here do not overwrite anyone\'s existing private copy.</p>':''}</div>`);
  m.querySelector('#opp-editor').onsubmit=async e=>{
    e.preventDefault();const g=id=>m.querySelector('#oe-'+id).value||null;const button=e.target.querySelector('button');button.disabled=true;
    try {await api(o?`/opportunities/${o.id}`:`/spaces/${space.id}/opportunities`,{method:o?'PATCH':'POST',body:{title:g('title'),company:g('company'),kind:g('kind'),url:g('url'),deadline:g('deadline'),description:g('notes')}});closeModal();toast('Saved for your team');refresh();}
    catch(err){m.querySelector('#oe-error').textContent=err.message;}finally{button.disabled=false;}
  };
}

async function spaceUpdates(body, space) {
  const ups = await api(`/spaces/${space.id}/updates`);
  body.innerHTML = `
    <form id="add" class="card p-2 flex gap-2 mb-5">
      <input id="b" required placeholder="Post an update..." class="input !ring-0 !w-auto flex-1">
      <select id="k" class="input !ring-0 !w-32 hidden sm:block"><option value="status">status</option><option value="announcement">announcement</option><option value="progress">progress</option></select>
      <button class="btn-primary">${icon('send','w-4 h-4')} Post</button>
    </form>
    <div class="space-y-2.5">
    ${ups.map(u => `<div class="card p-4">
      <div class="flex items-center gap-2.5 mb-2">
        ${avatar(u.author_name, 'w-7 h-7 text-[10px]')}
        <span class="text-sm font-semibold">${esc(u.author_name || '')}</span>
        ${kindChip(u.kind)}
        <span class="text-[11px] text-stone-400 ml-auto">${fmtDateTime(u.created_at)}</span>
      </div>
      <p class="text-sm text-stone-700 pl-9">${esc(u.body)}</p>
    </div>`).join('') || `<div class="rounded-xl border-2 border-dashed border-stone-200 p-8 text-center">
      <div class="text-stone-300 flex justify-center mb-2">${icon('inbox','w-8 h-8')}</div>
      <p class="text-sm text-stone-400">No updates yet. Say what you are working on.</p></div>`}
    </div>`;
  document.getElementById('add').onsubmit = async e => {
    e.preventDefault();
    const k = document.getElementById('k');
    await api(`/spaces/${space.id}/updates`, { method: 'POST',
      body: { body: document.getElementById('b').value, kind: k ? k.value : 'status' } });
    renderSpace(space.id, 'updates');
  };
}

async function spaceProjects(body, space) {
  const items = await api(`/spaces/${space.id}/items`);
  view._items = items;
  const cols = ['open','in_progress','done'];
  const colColor = { open: 'chip-stone', in_progress: 'chip-blue', done: 'chip-green' };
  body.innerHTML = `
    <form id="add" class="card p-2 flex gap-2 mb-5">
      <input id="t" required placeholder="Add a task..." class="input !ring-0 !w-auto flex-1">
      <button class="btn-primary">${icon('plus','w-4 h-4')} Add</button>
    </form>
    <div class="grid sm:grid-cols-3 gap-3">
    ${cols.map(st => {
      const list = items.filter(i => i.status === st && i.type !== 'plan' && i.type !== 'project');
      return `<div class="bg-stone-200/50 rounded-xl p-2.5 min-h-32">
        <div class="flex items-center gap-2 mb-2 px-1"><span class="chip ${colColor[st]}">${STATUS_LABEL[st]}</span><span class="text-xs text-stone-400 font-semibold">${list.length}</span></div>
        ${list.map(i => `
          <div class="card p-3 mb-2 text-sm cursor-pointer hover:shadow-pop transition-shadow" data-item="${i.id}">
            <div class="font-medium">${esc(i.title)}</div>
            <div class="mt-2"><select data-move="${i.id}" class="input !py-1 !px-1.5 !text-xs !w-auto">
              ${cols.map(c => `<option value="${c}" ${c===st?'selected':''}>${STATUS_LABEL[c]}</option>`).join('')}
            </select></div>
          </div>`).join('')}
      </div>`;
    }).join('')}
    </div>`;
  document.getElementById('add').onsubmit = async e => {
    e.preventDefault();
    await api(`/spaces/${space.id}/items`, { method: 'POST', body: { type: 'todo', title: document.getElementById('t').value } });
    renderSpace(space.id, 'projects');
  };
  body.querySelectorAll('[data-move]').forEach(s => s.onclick = e => e.stopPropagation());
  body.querySelectorAll('[data-move]').forEach(s => s.onchange = async () => {
    await api('/items/' + s.dataset.move, { method: 'PATCH', body: { status: s.value } });
    renderSpace(space.id, 'projects');
  });
  body.querySelectorAll('[data-item]').forEach(c => c.onclick = () => openItemDetail(c.dataset.item, () => renderSpace(space.id, 'projects')));
}

async function spaceMembers(body, space) {
  const isOwner = space.role === 'owner';
  body.innerHTML = `
    <div class="card divide-y divide-stone-100">
    ${space.members.map(m => `<div class="flex items-center gap-3 p-4">
      ${avatar(m.user.name, 'w-9 h-9 text-xs')}
      <div class="flex-1 min-w-0"><div class="font-semibold text-sm truncate">${esc(m.user.name)}${m.user.id === me.id ? ' <span class="text-stone-400 font-normal">(you)</span>' : ''}</div>
      <div class="text-xs text-stone-400 truncate">${esc(m.user.email)}</div></div>
      <span class="chip ${m.role === 'owner' ? 'chip-college' : 'chip-stone'}">${esc(m.role)}</span>
    </div>`).join('')}
    </div>
    ${isOwner ? `<button id="inv" class="btn-primary mt-4">${icon('link','w-4 h-4')} Invite friends</button>`
      : '<p class="text-sm text-stone-400 mt-4">Only the owner can invite new members.</p>'}`;
  const btn = document.getElementById('inv');
  if (btn) btn.onclick = () => openInvite(space);
}

/* ---------- Settings ---------- */
async function renderSettings() {
  const profile = await api('/match-profile');
  const tokens = await api('/agent/tokens');
  const changes = await api('/agent/changes');
  if(view.name!=='settings')return;
  main().innerHTML = `
  <div class="view-in settings-page">
    <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight mb-2">Settings</h1><p class="text-sm text-stone-500 mb-6">Make Qyad feel like your own. Your profile stays private.</p><div class="settings-grid">
    <div class="card p-5 sm:p-6 settings-card">
      <div class="flex items-center gap-2 mb-2"><h2 class="font-bold">My match profile</h2>${privacyChip('Private')}</div>
      <p class="text-sm text-stone-500 mb-4">Match the opportunities in your main list against your private profile. This is simple keyword matching, not AI screening or an eligibility score. Your resume and preferences are never sent to job sources or shared with friends.</p>
      <div class="resume-upload"><label class="label" for="resume-file">Upload your resume</label><input id="resume-file" type="file" accept=".pdf,.txt"><button id="resume-extract" class="btn-ghost">Extract text & skills</button><p>PDF or TXT, under 2 MB. Parsed on your server, never sent to an AI or job provider. Preview before saving. Scanned PDFs and DOCX are not supported yet.</p><p id="resume-upload-status" role="status"></p></div><form id="match-form" class="space-y-4"><div><label class="label" for="match-roles">Target roles</label><input id="match-roles" class="input" value="${esc(profile.roles)}" placeholder="e.g. Backend Intern, Full Stack Developer" maxlength="1000"></div><div><label class="label" for="match-keywords">Skills / keywords, separated by commas</label><input id="match-keywords" class="input" value="${esc(profile.keywords)}" placeholder="Python, React, SQL, internship" maxlength="3000"></div><div><label class="label" for="match-resume">Optional resume text</label><textarea id="match-resume" class="input" rows="4" maxlength="40000" placeholder="Paste plain text to extract common technical skills. Remove phone/address if you prefer.">${esc(profile.resume_text)}</textarea><p class="text-xs text-stone-400 mt-1">Stored privately on your own server. Only recognized technical skills are extracted from resume text. Add any missing skills above.</p></div><p class="text-xs text-stone-500">Active terms: ${profile.terms.map(esc).join(', ')||'None yet'}</p><div class="flex flex-wrap gap-2"><button class="btn-primary">Save match profile</button><button id="match-clear" type="button" class="btn-ghost">Clear profile</button></div><p id="match-error" role="alert" class="text-sm text-red-600"></p></form>
    </div>
    <div class="card p-5 sm:p-6 settings-card">
      <h2 class="font-bold mb-2">Appearance</h2><p class="text-sm text-stone-500 mb-4">Clean white or deep black, with a focused orange accent. Saved on this browser.</p><div class="appearance-options"><button data-theme-choice="light" class="appearance-option" aria-pressed="false"><span class="theme-preview preview-light"><i></i><b></b><em></em></span>${icon('sun','w-4 h-4')} Light</button><button data-theme-choice="dark" class="appearance-option" aria-pressed="false"><span class="theme-preview preview-dark"><i></i><b></b><em></em></span>${icon('moon','w-4 h-4')} Dark</button></div><div class="border-t border-stone-200 my-6"></div><h2 class="font-bold mb-4">Profile</h2>
      <div class="flex items-center gap-3">
        ${avatar(me.name, 'w-11 h-11 text-sm')}
        <div><div class="font-semibold">${esc(me.name)}</div>
        <div class="text-sm text-stone-500">${esc(me.email)} · ${esc(me.timezone)}</div></div>
      </div>
    </div>
    <div class="card p-5 sm:p-6 settings-card">
      <h2 class="font-bold mb-2">Sign-in options</h2><p class="text-sm text-stone-500 mb-3">${authConfig.clerk_enabled?'Clerk is configured. Existing accounts must link while signed in with their old password. Your spaces stay on this server.':'Clerk is not configured yet. Add your own keys to the server .env file, then restart. Password login still works.'}</p><button id="link-clerk" class="btn-ghost mb-6 ${authConfig.clerk_enabled&&!clerkMode?'':'hidden'}">Link Clerk account</button>
      <div class="flex items-center gap-2 mb-1">
        <h2 class="font-bold">Agent connection</h2>
        <span class="chip bg-amber-50 text-amber-700 ring-1 ring-amber-200">Unverified</span>
      </div>
      <p class="text-sm text-stone-500 mb-4">A personal access token lets your own assistant apply the changes you confirm in chat
        (WhatsApp voice notes to dashboard). It can only write as you. The end-to-end connection is
        <b>not verified</b> until you run the acceptance test in the README.</p>
      <button id="mk" class="btn-primary">${icon('plus','w-4 h-4')} Create token</button>
      <div id="tokout" class="hidden mt-4 rounded-xl bg-amber-50 ring-1 ring-amber-200 p-4">
        <p class="text-sm font-semibold text-amber-800 mb-2">Copy this now - it is shown once:</p>
        <div class="flex gap-2"><input id="tok" readonly class="input !text-xs !font-mono !bg-white" onclick="this.select()">
        <button id="tokcp" class="btn-ghost shrink-0">${icon('copy','w-4 h-4')}</button></div>
      </div>
      <div class="mt-4 space-y-2">${tokens.map(t => `
        <div class="flex items-center gap-3 text-sm">
          <code class="bg-stone-100 px-2 py-1 rounded-lg text-xs font-mono">...${esc(t.last4)}</code>
          <span class="text-stone-500 flex-1 text-xs">${esc(t.label || 'token')} · created ${fmtDate(t.created_at)} ${t.revoked ? '· <span class="text-red-500 font-semibold">revoked</span>' : ''}</span>
          ${t.revoked ? '' : `<button data-rev="${t.id}" class="text-red-600 text-xs font-semibold hover:underline">Revoke</button>`}
        </div>`).join('') || '<p class="text-xs text-stone-400">No tokens yet.</p>'}</div>
    </div>
    <div class="card p-5 sm:p-6 settings-card">
      <h2 class="font-bold mb-3">Recent agent-made changes</h2>
      ${changes.length ? `<div class="divide-y divide-stone-100">${changes.map(c => `
        <div class="py-2.5 flex items-center gap-2 text-sm">
          <span class="chip chip-college">${icon('spark','w-3 h-3')} agent</span>
          <span class="flex-1">${esc(c.action)} on ${esc(c.entity_table)}</span>
          <span class="text-xs text-stone-400">${fmtDateTime(c.created_at)}</span>
        </div>`).join('')}</div>`
        : '<p class="text-sm text-stone-400">No agent changes yet. They will appear here once the connection is verified and running.</p>'}
    </div>
  </div></div>`;
  document.getElementById('link-clerk').onclick=()=>openClerk(true);
  document.querySelectorAll('[data-theme-choice]').forEach(b=>b.onclick=()=>applyTheme(b.dataset.themeChoice));applyTheme(document.documentElement.dataset.theme||'light');
  document.getElementById('resume-extract').onclick=async()=>{
    const file=document.getElementById('resume-file').files[0],status=document.getElementById('resume-upload-status'),button=document.getElementById('resume-extract');
    if(!file){status.textContent='Choose a PDF or TXT file first';return;}
    if(file.size>2000000){status.textContent='File must be under 2 MB';return;}
    button.disabled=true;status.textContent='Extracting privately on your server...';
    try{const form=new FormData();form.append('file',file);const result=await api('/match-profile/resume-preview',{method:'POST',body:form});document.getElementById('match-resume').value=result.resume_text;const input=document.getElementById('match-keywords');input.value=[...new Set([...input.value.split(',').map(s=>s.trim()).filter(Boolean),...result.skills])].join(', ');status.textContent=result.notice+' Detected '+result.skills.length+' skill terms. Review the preview below.';}
    catch(e){status.textContent=e.message;}finally{button.disabled=false;}
  };
  document.getElementById('match-form').onsubmit = async e=>{
    e.preventDefault();try {await api('/match-profile',{method:'PUT',body:{roles:document.getElementById('match-roles').value,keywords:document.getElementById('match-keywords').value,resume_text:document.getElementById('match-resume').value}});toast('Private match profile saved');renderSettings();}catch(err){document.getElementById('match-error').textContent=err.message;}
  };
  document.getElementById('match-clear').onclick=async()=>{await api('/match-profile',{method:'PUT',body:{}});toast('Match profile cleared');renderSettings();};
  document.getElementById('mk').onclick = async () => {
    const r = await api('/agent/tokens', { method: 'POST', body: {} });
    const out = document.getElementById('tokout');
    out.classList.remove('hidden');
    document.getElementById('tok').value = r.token;
  };
  document.getElementById('tokcp').onclick = async () => {
    const v = document.getElementById('tok').value;
    try { await navigator.clipboard.writeText(v); } catch (e) { document.getElementById('tok').select(); document.execCommand('copy'); }
    toast('Token copied');
  };
  main().querySelectorAll('[data-rev]').forEach(b => b.onclick = async () => {
    if (await confirmDlg({ title: 'Revoke this token?', body: 'Any assistant using it immediately loses write access.', actionLabel: 'Revoke' })) {
      await api(`/agent/tokens/${b.dataset.rev}/revoke`, { method: 'POST' });
      toast('Token revoked'); renderSettings();
    }
  });
}

function matchChip(o, total) {
  if(!total)return '<span class="text-xs text-stone-400 inline-block">Set your private match profile</span>';
  if(o.match_score!=null)return `<span class="chip ${o.match_score?'chip-green':'chip-stone'}" title="${esc(o.score_method)}">${o.match_score}% profile overlap</span>`;
  return `<span class="chip ${o.match_count?'chip-green':'chip-stone'}" title="${esc((o.matched_terms||[]).join(', ')||'No overlapping terms')}">${o.match_count}/${total} keyword hits</span>`;
}

async function appendStarterOpportunities(){
  if(view.name!=='today'||spaces.some(s=>s.type!=='personal'))return;
  const data=await api('/opportunity-catalog');if(view.name!=='today')return;
  const section=document.createElement('section');section.className='starter-opportunities';
  section.innerHTML='<h2>Your next opportunities</h2><p>Checked 23 Nov 2026. Confirm status and eligibility at the source.</p><div class="table-scroll" role="region" aria-label="Suggested opportunities table" tabindex="0"><table class="opportunities-table"><thead><tr><th>Role</th><th>Company / location</th><th>Type</th><th>Deadline</th><th>Match</th><th>Status</th><th>Link</th></tr></thead><tbody>'+data.jobs.map(j=>`<tr><td class="role-cell"><span class="table-role">${esc(j.title)}</span><details class="table-details"><summary>Details</summary><p>${esc(j.description)}</p><button data-starter="${esc(j.id)}" class="btn-ghost">Track privately</button></details></td><td><span class="table-company">${esc(j.company)}</span><span class="table-meta">${esc(j.location)}</span></td><td>${esc(j.kind==='event'?'Hackathon / event':j.kind)}</td><td class="date-cell">${j.deadline?esc(j.deadline):'Not stated'}</td><td>${j.match_score==null?'—':j.match_score+'%'}</td><td>Suggested</td><td><a class="table-apply" target="_blank" rel="noopener noreferrer" href="${safeLink(j.url)}">${j.kind==='event'?'Open':'Apply'} ↗</a></td></tr>`).join('')+'</tbody></table></div><p class="table-phone-hint">Swipe the table sideways for all columns.</p>';
  main().append(section);section.querySelectorAll('[data-starter]').forEach(b=>b.onclick=async()=>{try{await api('/opportunity-catalog/'+b.dataset.starter+'/save',{method:'POST',body:{}});toast('Saved privately');}catch(e){toast(e.message,'err');}});
}

/* ---------- Optional Clerk sign-in. No secret key enters this bundle. ---------- */
async function loadClerk(){
 if(clerkReady)return clerkReady;
 clerkReady=(async()=>{
  if(!authConfig.clerk_enabled)throw new Error('Clerk is not configured');
  const load=(path,key)=>new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=authConfig.frontend_url+path;script.crossOrigin='anonymous';if(key)script.setAttribute('data-clerk-publishable-key',key);script.onload=resolve;script.onerror=()=>reject(new Error('Clerk could not load. Check your connection and server keys.'));document.head.appendChild(script);});
  await load('/npm/@clerk/ui@1/dist/ui.browser.js');
  await load('/npm/@clerk/clerk-js@6/dist/clerk.browser.js',authConfig.publishable_key);
  await window.Clerk.load({ui:{ClerkUI:window.__internal_ClerkUICtor}});return window.Clerk;
 })();try{return await clerkReady;}catch(e){clerkReady=null;throw e;}
}
async function openClerk(link){
 try{
  const clerk=await loadClerk();
  if(!clerk.session){
   sessionStorage.setItem('qyad-clerk-action',link?'link':'login');
   const redirect=new URL(location.href);redirect.hash='';
   const modal=openModal('<div class="p-5"><div class="flex justify-between mb-4"><h2 class="font-bold">Continue with Clerk</h2><button data-close aria-label="Close">'+icon('x','w-5 h-5')+'</button></div><div id="clerk-mount"></div></div>');
   clerk.mountSignIn(modal.querySelector('#clerk-mount'),{routing:'hash',forceRedirectUrl:redirect.href,signUpForceRedirectUrl:redirect.href});
   let stop=null;stop=clerk.addListener(async ({session})=>{if(session){if(stop)stop();try{await finishClerk(link);}catch(e){toast(e.message,'err');}}});return;
  }
  await finishClerk(link);
 }catch(e){toast(e.message,'err');}
}
async function finishClerk(link){
 const token=await window.Clerk.session.getToken();
 if(!token)throw new Error('Clerk has no active session');
 const response=await fetch('/api/v1/auth/clerk'+(link?'/link':''),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
 const data=await response.json();if(!response.ok)throw new Error(data.detail||'Clerk sign-in failed');
 sessionStorage.removeItem('qyad-clerk-action');closeModal();
 if(link){toast('Clerk account linked. Your data has not moved.');return;}
 savePreference('qyad-auth-provider','clerk');clerkMode=true;me=data;await boot();
}
/* ---------- init ---------- */
(async () => {
  const params = new URLSearchParams(location.search);
  try{authConfig=await (await fetch('/api/v1/auth/config')).json();}catch(e){}
  const action=sessionStorage.getItem('qyad-clerk-action');if(authConfig.clerk_enabled && action){try{await loadClerk();if(window.Clerk.session){await finishClerk(action==='link');if(action==='login')return;}}catch(e){renderAuth();toast(e.message,'err');return;}}
  if(authConfig.clerk_enabled && stored('qyad-auth-provider','local')==='clerk'){try{await loadClerk();if(window.Clerk.session){await finishClerk(false);return;}}catch(e){renderAuth();toast(e.message,'err');return;}}
  try { me = await api('/auth/me'); } catch (e) { renderAuth(); return; }
  await boot();
})();
