import { HOUSES, TYPES, availableYears, explorerUrl, loadIndicator, loadManifest, loadPeople } from './data.js';
import { $, drawChart, externalUrl, fold, formatDate, formatInt, formatTimestamp, initShell, initTabs, renderPagination, renderSimpleTable, setState, updateStamp } from './ui.js';

const casa = new URLSearchParams(location.search).get('casa');
initShell(casa in HOUSES ? casa : '');
const state = $('#house-state');
const pageSize = 25;
let people = [];
let peoplePage = 1;
let partyRows = [];
let ufRows = [];
let monthlyRows = [];
let manifest;
let activateTab;
let renderedComposition = false;

if (!(casa in HOUSES)) {
  setState(state, 'Casa inválida. Escolha Câmara ou Senado no menu.', 'error');
} else {
  document.title = `${HOUSES[casa]} | Painel Legislativo Brasileiro`;
  $('#breadcrumb-house').textContent = HOUSES[casa];
  $('#house-kicker').textContent = casa === 'camara' ? 'Câmara dos Deputados' : 'Senado Federal';
  $('#house-title').textContent = casa === 'camara' ? 'A Câmara, em números.' : 'O Senado, em números.';
  $('#house-description').textContent = 'Composição atual e projetos apresentados desde 2023, com dados separados por fonte e período.';
  $('#house-project-link').href = explorerUrl({ casa });
  activateTab = initTabs(document, name => {
    if (name === 'composicao' && !renderedComposition && manifest) renderComposition();
    if (name === 'projetos' && manifest) renderMonthly();
  });
  try {
    const [m, partyFile, ufFile, monthFile, peopleFile] = await Promise.all([
      loadManifest(), loadIndicator('composicao_por_partido'), loadIndicator('composicao_por_uf'), loadIndicator('projetos_por_mes'), loadPeople(casa)
    ]);
    manifest = m; updateStamp(m);
    people = peopleFile.dados;
    partyRows = partyFile.dados.filter(row => row.casa === casa).sort((a, b) => b.quantidade - a.quantidade || a.partido.localeCompare(b.partido, 'pt-BR'));
    ufRows = ufFile.dados.filter(row => row.casa === casa).sort((a, b) => b.quantidade - a.quantidade || a.uf.localeCompare(b.uf, 'pt-BR'));
    monthlyRows = monthFile.dados.filter(row => row.casa === casa);
    $('#house-snapshot').textContent = `Composição: ${formatInt(people.length)} parlamentares em exercício na coleta de ${formatTimestamp(peopleFile.meta.referencia_utc)}. Projetos: ${formatDate(m.inicio)} a ${formatDate(m.fim)}.`;
    document.querySelectorAll('.chart-card-head p').forEach(el => { el.textContent = `Parlamentares em exercício · Fonte: ${HOUSES[casa]} · ${formatDate(m.fim)}`; });
    const years = availableYears(m);
    $('#series-year').append(...years.map(year => new Option(String(year), String(year))));
    $('#series-year').addEventListener('change', renderMonthly);
    setupPeople();
    setState(state, '');
    renderComposition();
  } catch (error) {
    setState(state, `Não foi possível carregar os dados da ${HOUSES[casa]}. ${error.message}`, 'error');
  }
}

function renderComposition() {
  renderedComposition = true;
  const renderBars = (rows, field, chartId, tableId, color) => {
    renderSimpleTable($(tableId), [field === 'partido' ? 'Partido' : 'UF', 'Parlamentares'], rows.map(row => [row[field], formatInt(row.quantidade)]), `Composição atual ${casa === 'camara' ? 'da Câmara' : 'do Senado'} por ${field}`);
    const chartRows = [...rows].reverse();
    drawChart($(chartId), [{ type: 'bar', orientation: 'h', x: chartRows.map(row => row.quantidade), y: chartRows.map(row => row[field]), marker: { color }, hovertemplate: `%{y}: %{x:,} parlamentares<extra></extra>` }], {
      height: Math.max(420, Math.min(980, rows.length * 30 + 85)),
      xaxis: { title: { text: 'Parlamentares em exercício' }, rangemode: 'tozero', fixedrange: true },
      yaxis: { type: 'category', fixedrange: true }, margin: { l: field === 'partido' ? 98 : 55, b: 52, r: 24 }, showlegend: false
    }, event => {
      const value = event.points[0]?.y;
      if (!value) return;
      $(field === 'partido' ? '#person-party' : '#person-uf').value = value;
      peoplePage = 1; renderPeople(); activateTab('parlamentares');
      $('#panel-parlamentares').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };
  renderBars(partyRows, 'partido', '#party-chart', '#party-table', casa === 'camara' ? '#235b9c' : '#11766e');
  renderBars(ufRows, 'uf', '#uf-chart', '#uf-table', casa === 'camara' ? '#4c83bc' : '#3b9b8d');
}

function setupPeople() {
  const parties = [...new Set(people.map(person => person.partido).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const ufs = [...new Set(people.map(person => person.uf).filter(Boolean))].sort();
  $('#person-party').append(...parties.map(party => new Option(party, party)));
  $('#person-uf').append(...ufs.map(uf => new Option(uf, uf)));
  ['#person-search', '#person-party', '#person-uf'].forEach(selector => $(selector).addEventListener(selector === '#person-search' ? 'input' : 'change', () => { peoplePage = 1; renderPeople(); }));
  renderPeople();
}

function renderPeople() {
  const search = fold($('#person-search').value.trim());
  const party = $('#person-party').value;
  const uf = $('#person-uf').value;
  const filtered = people.filter(person => (!search || fold(person.nome).includes(search)) && (!party || person.partido === party) && (!uf || person.uf === uf)).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
  $('#people-count').textContent = `${formatInt(filtered.length)} de ${formatInt(people.length)} parlamentares no retrato atual`;
  const totalPages = Math.ceil(filtered.length / pageSize);
  peoplePage = Math.min(peoplePage, Math.max(1, totalPages));
  const rows = filtered.slice((peoplePage - 1) * pageSize, peoplePage * pageSize);
  const container = $('#people-list');
  if (!rows.length) { container.innerHTML = '<div class="empty-state">Nenhum parlamentar corresponde aos filtros selecionados.</div>'; }
  else {
    const table = document.createElement('table'); table.className = 'data-table';
    table.innerHTML = '<caption>Lista de parlamentares em exercício na coleta</caption><thead><tr><th scope="col">Nome</th><th scope="col">Partido</th><th scope="col">UF</th><th scope="col">Fonte</th></tr></thead><tbody></tbody>';
    const body = table.querySelector('tbody');
    rows.forEach(person => {
      const tr = document.createElement('tr');
      [person.nome, person.partido || 'Não informado', person.uf || 'Não informada'].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
      const source = document.createElement('td'); const link = externalUrl(person.url_fonte);
      if (link) { const a = document.createElement('a'); a.href = link; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = 'Perfil oficial ↗'; source.append(a); }
      tr.append(source); body.append(tr);
    });
    container.replaceChildren(table);
  }
  renderPagination($('#people-pagination'), peoplePage, totalPages, next => { peoplePage = next; renderPeople(); $('#people-count').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
}

function renderMonthly() {
  const year = $('#series-year').value;
  const dates = [];
  const start = new Date(`${manifest.inicio.slice(0, 7)}-01T00:00:00Z`);
  const end = manifest.fim.slice(0, 7);
  for (let date = start; date.toISOString().slice(0, 7) <= end; date.setUTCMonth(date.getUTCMonth() + 1)) {
    const value = date.toISOString().slice(0, 7);
    if (year === 'todos' || value.startsWith(year)) dates.push(value);
  }
  const lookup = new Map(monthlyRows.map(row => [`${row.mes}|${row.tipo}`, row.quantidade]));
  const colors = { PL: casa === 'camara' ? '#235b9c' : '#11766e', PLP: '#b07a32', PEC: '#7b5c95' };
  renderSimpleTable($('#monthly-table'), ['Mês', 'PL', 'PLP', 'PEC'], dates.map(month => [month, ...TYPES.map(type => formatInt(lookup.get(`${month}|${type}`) ?? 0))]), `Projetos apresentados por mês ${casa === 'camara' ? 'na Câmara' : 'no Senado'}`);
  $('#month-note').textContent = `Fonte: ${HOUSES[casa]}. Unidade: projetos únicos apresentados no mês. ${formatDate(manifest.fim)} é o limite da coleta; o último mês pode estar incompleto.`;
  drawChart($('#monthly-chart'), TYPES.map(type => ({ type: 'scatter', mode: 'lines+markers', name: type, x: dates, y: dates.map(month => lookup.get(`${month}|${type}`) ?? 0), line: { color: colors[type], width: 2.5 }, marker: { size: 5 }, hovertemplate: `${type} · %{x}: %{y:,} projetos<extra></extra>` })), {
    height: 440, xaxis: { title: { text: 'Mês de apresentação' }, type: 'category', tickmode: 'array', tickvals: dates.filter((_, index) => index % (dates.length > 18 ? 3 : 1) === 0) }, yaxis: { title: { text: 'Projetos apresentados' }, rangemode: 'tozero' }, legend: { orientation: 'h', y: 1.12, x: 0 }, margin: { l: 65, r: 25, t: 48, b: 80 }
  }, event => {
    const point = event.points[0];
    if (point?.x && TYPES.includes(point.data.name)) location.href = explorerUrl({ casa, ano: point.x.slice(0, 4), mes: point.x, tipo: point.data.name });
  });
}
