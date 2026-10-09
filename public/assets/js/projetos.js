import { HOUSES, TYPES, availablePartitions, availableYears, loadManifest, loadPartitions, projectUrl } from './data.js';
import { $, escapeHtml, fold, formatDate, formatInt, initShell, renderPagination, setState, updateStamp } from './ui.js';

initShell('projetos');
const state = $('#projects-state');
const controls = {
  house: $('#filter-house'), year: $('#filter-year'), type: $('#filter-type'), month: $('#filter-month'),
  search: $('#filter-search'), status: $('#filter-status'), sort: $('#filter-sort')
};
const pageSize = 24;
const params = new URLSearchParams(location.search);
let manifest;
let allProjects = [];
let visibleProjects = [];
let page = 1;
let requestGeneration = 0;
let searchTimer;

function choice(value, allowed, fallback) { return allowed.includes(value) ? value : fallback; }
function availableMonths(year) {
  const months = [];
  const start = new Date(`${manifest.inicio.slice(0, 7)}-01T00:00:00Z`);
  const end = manifest.fim.slice(0, 7);
  for (let date = start; date.toISOString().slice(0, 7) <= end; date.setUTCMonth(date.getUTCMonth() + 1)) {
    const month = date.toISOString().slice(0, 7);
    if (year === 'todos' || month.startsWith(year)) months.push(month);
  }
  return months;
}
function fillMonths(preferred = 'todos') {
  const months = availableMonths(controls.year.value);
  controls.month.replaceChildren(new Option('Todos', 'todos'), ...months.map(month => new Option(month, month)));
  controls.month.value = months.includes(preferred) ? preferred : 'todos';
}
function fillStatuses(preferred = 'todos') {
  const options = [...new Set(allProjects.map(project => project.situacao_resumo).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  controls.status.replaceChildren(new Option('Todas', 'todos'), ...options.map(status => new Option(status, status)));
  controls.status.value = options.includes(preferred) ? preferred : 'todos';
  $('#status-field').hidden = controls.house.value !== 'senado';
}
function writeUrl() {
  const url = new URL(location.href);
  url.search = '';
  for (const [key, value, defaultValue] of [
    ['casa', controls.house.value, 'todas'], ['ano', controls.year.value, String(availableYears(manifest)[0])],
    ['tipo', controls.type.value, 'todos'], ['mes', controls.month.value, 'todos'],
    ['q', controls.search.value.trim(), ''], ['situacao', controls.status.value, 'todos'], ['ordem', controls.sort.value, 'recentes']
  ]) if (value !== defaultValue && (key !== 'situacao' || controls.house.value === 'senado')) url.searchParams.set(key, value);
  history.replaceState(null, '', url);
}
function applyFilters() {
  const query = fold(controls.search.value.trim());
  const month = controls.month.value;
  const status = controls.house.value === 'senado' ? controls.status.value : 'todos';
  visibleProjects = allProjects.filter(project => {
    if (month !== 'todos' && !project.data_apresentacao.startsWith(month)) return false;
    if (status !== 'todos' && project.situacao_resumo !== status) return false;
    return !query || fold(`${project.identificacao} ${project.ementa}`).includes(query);
  });
  const direction = controls.sort.value === 'antigos' ? 1 : -1;
  visibleProjects.sort((a, b) => direction * (a.data_apresentacao.localeCompare(b.data_apresentacao) || a.casa.localeCompare(b.casa) || a.id.localeCompare(b.id)));
  page = 1;
  renderResults();
  writeUrl();
}
function renderResults() {
  const count = visibleProjects.length;
  const totalPages = Math.ceil(count / pageSize);
  page = Math.min(page, Math.max(1, totalPages));
  $('#results-count').textContent = `${formatInt(count)} projeto${count === 1 ? '' : 's'} no recorte`;
  const list = $('#projects-list');
  if (!count) {
    list.innerHTML = '<div class="empty-state"><strong>Nenhum projeto encontrado.</strong><br>Altere os filtros ou o texto da busca.</div>';
  } else {
    list.replaceChildren(...visibleProjects.slice((page - 1) * pageSize, page * pageSize).map(project => {
      const card = document.createElement('article'); card.className = 'project-card';
      const status = project.casa === 'senado' && project.situacao_resumo ? `<span class="tag">${escapeHtml(project.situacao_resumo)}</span>` : '';
      card.innerHTML = `<div class="project-card-head"><div class="tag-row"><span class="tag ${project.casa}">${HOUSES[project.casa]}</span><span class="tag">${escapeHtml(project.tipo)}</span>${status}</div><span class="data-caption">Apresentado em ${formatDate(project.data_apresentacao)}</span></div><h3><a href="${projectUrl(project)}">${escapeHtml(project.identificacao)} <span aria-hidden="true">↗</span></a></h3><p>${escapeHtml(project.ementa)}</p>`;
      return card;
    }));
  }
  renderPagination($('#projects-pagination'), page, totalPages, next => { page = next; renderResults(); $('#results-title').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
}
async function reloadPartitions() {
  const generation = ++requestGeneration;
  const paths = availablePartitions(manifest, controls.house.value, controls.year.value, controls.type.value);
  allProjects = []; visibleProjects = [];
  $('#projects-list').replaceChildren(); $('#projects-pagination').replaceChildren();
  $('#results-count').textContent = '';
  setState(state, `Carregando 0 de ${paths.length} arquivos de projetos…`);
  try {
    const projects = await loadPartitions(paths, (done, total) => { if (generation === requestGeneration) setState(state, `Carregando ${done} de ${total} arquivos de projetos…`); });
    if (generation !== requestGeneration) return;
    allProjects = [...new Map(projects.map(project => [`${project.casa}:${project.id}`, project])).values()];
    const preferredStatus = controls.status.value;
    fillStatuses(preferredStatus);
    setState(state, '');
    applyFilters();
  } catch (error) {
    if (generation === requestGeneration) setState(state, `Não foi possível carregar este recorte. Tente atualizar a página ou escolher outro filtro. ${error.message}`, 'error');
  }
}

try {
  manifest = await loadManifest(); updateStamp(manifest);
  const years = availableYears(manifest);
  controls.year.replaceChildren(...years.map(year => new Option(String(year), String(year))), new Option('Todos os anos', 'todos'));
  controls.house.value = choice(params.get('casa'), ['todas', ...Object.keys(HOUSES)], 'todas');
  controls.year.value = choice(params.get('ano'), [...years.map(String), 'todos'], String(years[0]));
  controls.type.value = choice(params.get('tipo'), ['todos', ...TYPES], 'todos');
  fillMonths(params.get('mes'));
  controls.search.value = params.get('q') || '';
  controls.sort.value = choice(params.get('ordem'), ['recentes', 'antigos'], 'recentes');
  $('#projects-coverage').textContent = `Dados de ${formatDate(manifest.inicio)} a ${formatDate(manifest.fim)} · atualização em ${formatDate(manifest.fim)} · ano final parcial.`;
  controls.house.addEventListener('change', reloadPartitions);
  controls.year.addEventListener('change', () => { fillMonths(); reloadPartitions(); });
  controls.type.addEventListener('change', reloadPartitions);
  controls.month.addEventListener('change', applyFilters);
  controls.status.addEventListener('change', applyFilters);
  controls.sort.addEventListener('change', applyFilters);
  controls.search.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(applyFilters, 220); });
  await reloadPartitions();
  if (controls.house.value === 'senado' && params.get('situacao')) { controls.status.value = choice(params.get('situacao'), [...controls.status.options].map(option => option.value), 'todos'); applyFilters(); }
} catch (error) {
  setState(state, `Não foi possível carregar o índice dos projetos. ${error.message}`, 'error');
}
