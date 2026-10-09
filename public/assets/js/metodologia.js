import { loadCoverage, loadManifest } from './data.js';
import { $, formatDate, formatInt, formatTimestamp, initShell, setState, updateStamp } from './ui.js';

initShell('metodologia');
const state = $('#method-state');

try {
  const [manifest, coverage] = await Promise.all([loadManifest(), loadCoverage()]);
  updateStamp(manifest);
  const tiles = [
    [formatInt(manifest.totais.deputados_atuais), 'Deputados em exercício na coleta'],
    [formatInt(manifest.totais.senadores_atuais), 'Senadores em exercício na coleta'],
    [formatInt(manifest.totais.projetos_camara), 'Projetos da Câmara no recorte'],
    [formatInt(manifest.totais.projetos_senado), 'Projetos do Senado no recorte']
  ];
  $('#coverage-cards').replaceChildren(...tiles.map(([number, label]) => { const card = document.createElement('div'); card.className = 'stat-tile'; const strong = document.createElement('strong'); strong.textContent = number; const span = document.createElement('span'); span.textContent = label; card.append(strong, span); return card; }));
  $('#coverage-note').textContent = `Projetos apresentados de ${formatDate(manifest.inicio)} a ${formatDate(manifest.fim)}. Retrato atual gerado em ${formatTimestamp(manifest.gerado_em_utc)}. O último ano e mês são parciais. Esquema público v${manifest.schema_version}.`;
  const labels = {
    presenca: 'Presença', 'participacao em votacoes': 'Participação em votações', 'aprovacao final': 'Aprovação final',
    'ideologia partidaria': 'Ideologia partidária', 'direcao de medida': 'Direção de medida'
  };
  $('#unavailable-list').replaceChildren(...coverage.indicadores_nao_publicados.map(item => { const li = document.createElement('li'); li.textContent = labels[item] || item; return li; }));
  $('#method-content').hidden = false;
  setState(state, '');
} catch (error) {
  setState(state, `Não foi possível carregar os metadados de cobertura. ${error.message}`, 'error');
}
