import { HOUSES, TYPES, availableYears, loadIndicator, loadManifest, explorerUrl } from './data.js';
import { $, drawChart, escapeHtml, formatDate, formatInt, initShell, renderSimpleTable, setState, updateStamp } from './ui.js';

initShell('inicio');

const state = $('#overview-state');
const cards = $('#overview-cards');
const yearSelect = $('#overview-year');
let manifest;
let summary;
let monthly;

function countFor(casa, year) {
  const counts = Object.fromEntries(TYPES.map(type => [type, 0]));
  monthly.dados.filter(row => row.casa === casa && row.mes.startsWith(String(year))).forEach(row => { counts[row.tipo] += row.quantidade; });
  return counts;
}

async function render() {
  const year = Number(yearSelect.value);
  cards.replaceChildren();
  for (const casa of Object.keys(HOUSES)) {
    const item = summary.dados.find(row => row.casa === casa);
    const counts = countFor(casa, year);
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    const card = document.createElement('article'); card.className = `house-card ${casa}`;
    card.innerHTML = `<div class="house-card-head"><div><span class="pill ${casa}">${HOUSES[casa]}</span><h3>${HOUSES[casa]}</h3></div><span class="data-caption">${escapeHtml(String(year))}</span></div>
      <div class="metric-row"><div class="metric"><strong>${formatInt(item.parlamentares_atuais)}</strong><span>Parlamentares em exercício<br>em ${formatDate(manifest.fim)}</span></div><div class="metric"><strong>${formatInt(total)}</strong><span>PL, PLP e PEC apresentados<br>em ${year}</span></div></div>
      <div class="chart-mini" id="mini-${casa}" aria-label="Projetos de ${HOUSES[casa]} por tipo em ${year}"></div><div class="table-wrap" id="mini-table-${casa}"></div>
      <div class="card-bottom"><span class="data-caption">Fonte: ${HOUSES[casa]} · ${year === Number(manifest.fim.slice(0, 4)) ? 'ano parcial até ' + formatDate(manifest.fim) : 'ano completo'}</span><a href="/casa.html?casa=${casa}">Ver a Casa →</a></div>`;
    cards.append(card);
    renderSimpleTable(card.querySelector(`#mini-table-${casa}`), ['Tipo', 'Projetos apresentados'], TYPES.map(type => [type, formatInt(counts[type])]), `Projetos apresentados em ${year} ${casa === 'camara' ? 'na Câmara' : 'no Senado'}`);
    await drawChart(card.querySelector(`#mini-${casa}`), [{ type: 'bar', orientation: 'h', x: TYPES.map(type => counts[type]), y: TYPES, marker: { color: casa === 'camara' ? '#235b9c' : '#11766e' }, hovertemplate: '%{y}: %{x:,} projetos<extra></extra>' }], { height: 220, xaxis: { title: { text: 'Projetos' }, rangemode: 'tozero', fixedrange: true }, yaxis: { categoryorder: 'array', categoryarray: [...TYPES].reverse(), fixedrange: true }, margin: { l: 52, b: 42, r: 30 }, showlegend: false }, event => {
      const type = event.points[0]?.y;
      if (TYPES.includes(type)) location.href = explorerUrl({ casa, ano: year, tipo: type });
    });
  }
}

try {
  [manifest, summary, monthly] = await Promise.all([loadManifest(), loadIndicator('resumo'), loadIndicator('projetos_por_mes')]);
  updateStamp(manifest);
  const years = availableYears(manifest);
  yearSelect.replaceChildren(...years.map(year => new Option(String(year), String(year))));
  yearSelect.addEventListener('change', render);
  setState(state, '');
  await render();
} catch (error) {
  setState(state, `Não foi possível carregar o retrato publicado. ${error.message}`, 'error');
}
