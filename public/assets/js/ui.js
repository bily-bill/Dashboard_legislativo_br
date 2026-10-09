let plotlyPromise;

export const $ = selector => document.querySelector(selector);
export const formatInt = value => new Intl.NumberFormat('pt-BR').format(value);
export function formatDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}/.test(value)) return 'Não informada';
  const [year, month, day] = value.slice(0, 10).split('-');
  return `${day}/${month}/${year}`;
}
export function formatTimestamp(value) {
  if (!value) return 'Não informado';
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date(value));
}
export function fold(value) {
  return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
}
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
export function externalUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}
export function setState(element, message, kind = '') {
  element.textContent = message;
  element.className = `notice ${kind}`.trim();
  element.hidden = !message;
}
export function initShell(active, manifest) {
  const nav = $('.main-nav');
  const toggle = $('.menu-toggle');
  document.querySelector(`[data-nav="${active}"]`)?.setAttribute('aria-current', 'page');
  toggle?.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
  });
  nav?.addEventListener('click', event => {
    if (event.target.closest('a')) { nav.classList.remove('open'); toggle?.setAttribute('aria-expanded', 'false'); }
  });
  if (manifest) updateStamp(manifest);
}
export function updateStamp(manifest) {
  document.querySelectorAll('[data-stamp]').forEach(el => { el.textContent = `Coleta em ${formatDate(manifest.fim)}`; });
}
export function initTabs(root = document, onActivate) {
  const tabs = [...root.querySelectorAll('[role="tab"]')];
  const activate = tab => {
    tabs.forEach(other => {
      const selected = other === tab;
      other.setAttribute('aria-selected', String(selected));
      other.tabIndex = selected ? 0 : -1;
      root.getElementById(other.getAttribute('aria-controls')).hidden = !selected;
    });
    onActivate?.(tab.dataset.tab);
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', event => {
      const offset = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      if (!offset) return;
      event.preventDefault();
      const next = tabs[(index + offset + tabs.length) % tabs.length];
      activate(next); next.focus();
    });
  });
  return name => { const tab = tabs.find(item => item.dataset.tab === name); if (tab) activate(tab); };
}
export function renderPagination(element, page, totalPages, onChange) {
  element.replaceChildren();
  if (totalPages <= 1) return;
  const prev = document.createElement('button'); prev.type = 'button'; prev.textContent = '← Anterior'; prev.disabled = page <= 1;
  const label = document.createElement('span'); label.textContent = `Página ${page} de ${totalPages}`; label.className = 'result-meta';
  const next = document.createElement('button'); next.type = 'button'; next.textContent = 'Próxima →'; next.disabled = page >= totalPages;
  prev.addEventListener('click', () => onChange(page - 1)); next.addEventListener('click', () => onChange(page + 1));
  element.append(prev, label, next);
}
export function renderSimpleTable(element, headers, rows, caption) {
  const table = document.createElement('table'); table.className = 'data-table';
  const title = document.createElement('caption'); title.textContent = caption; table.append(title);
  const thead = document.createElement('thead'); const tr = document.createElement('tr');
  headers.forEach(header => { const th = document.createElement('th'); th.scope = 'col'; th.textContent = header; tr.append(th); });
  thead.append(tr); table.append(thead);
  const tbody = document.createElement('tbody');
  rows.forEach(row => { const line = document.createElement('tr'); row.forEach(cell => { const td = document.createElement('td'); td.textContent = cell; line.append(td); }); tbody.append(line); });
  table.append(tbody); element.replaceChildren(table);
}
export function loadPlotly() {
  if (!plotlyPromise) {
    plotlyPromise = new Promise((resolve, reject) => {
      if (window.Plotly) { resolve(window.Plotly); return; }
      const script = document.createElement('script'); script.src = '/assets/vendor/plotly-4.1.1.min.js'; script.async = true;
      script.onload = () => window.Plotly ? resolve(window.Plotly) : reject(new Error('Plotly indisponível.'));
      script.onerror = () => reject(new Error('Plotly indisponível.'));
      document.head.append(script);
    });
  }
  return plotlyPromise;
}
export async function drawChart(element, traces, layout, onClick) {
  try {
    const Plotly = await loadPlotly();
    await Plotly.newPlot(element, traces, { ...layout, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { family: 'system-ui, sans-serif', color: '#1d2935', size: 12 }, margin: { l: 70, r: 22, t: 12, b: 48, ...(layout.margin || {}) } }, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] });
    if (onClick) { element.removeAllListeners?.('plotly_click'); element.on('plotly_click', onClick); }
  } catch {
    element.innerHTML = '<p class="chart-fallback">Gráfico indisponível. Os mesmos valores estão na tabela abaixo.</p>';
  }
}
