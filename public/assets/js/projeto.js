import { HOUSES, TYPES, availablePartitions, availableYears, explorerUrl, loadCoverage, loadManifest, loadProjects, projectPath } from './data.js';
import { $, escapeHtml, externalUrl, formatDate, formatTimestamp, initShell, initTabs, setState, updateStamp } from './ui.js';

initShell('projetos');
const state = $('#detail-state');
const params = new URLSearchParams(location.search);
const casa = params.get('casa');
const ano = params.get('ano');
const tipo = params.get('tipo');
const id = params.get('id');

function fact(label, value) {
  const item = document.createElement('div'); item.className = 'fact';
  const name = document.createElement('span'); name.textContent = label;
  const content = document.createElement('strong'); content.textContent = value || 'Não informado na exportação';
  item.append(name, content); return item;
}
function addLink(container, label, value, primary = false) {
  const url = externalUrl(value);
  if (!url) return;
  const link = document.createElement('a'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer';
  link.className = `button ${primary ? 'button-primary' : 'button-outline'}`; link.textContent = `${label} ↗`; container.append(link);
}

try {
  const [manifest, coverage] = await Promise.all([loadManifest(), loadCoverage()]);
  updateStamp(manifest);
  const valid = casa in HOUSES && availableYears(manifest).map(String).includes(ano) && TYPES.includes(tipo) && /^\d+$/.test(id || '') && availablePartitions(manifest, casa, ano, tipo).includes(projectPath(casa, ano, tipo));
  if (!valid) throw new Error('O endereço do projeto está incompleto ou fora da cobertura publicada. Abra-o pela busca de projetos.');
  const file = await loadProjects(casa, ano, tipo);
  const project = file.dados.find(row => row.id === id);
  if (!project) throw new Error('Projeto não encontrado no arquivo publicado deste recorte. Confira Casa, ano e tipo.');
  document.title = `${project.identificacao} | Painel Legislativo Brasileiro`;
  $('#back-projects').href = explorerUrl({ casa, ano, tipo });
  $('#breadcrumb-project').textContent = project.identificacao;
  $('#detail-kicker').textContent = `${HOUSES[casa]} / Projeto apresentado em ${ano}`;
  $('#detail-title').textContent = project.identificacao;
  $('#detail-subtitle').textContent = `Apresentado em ${formatDate(project.data_apresentacao)} · ${HOUSES[casa]}`;
  $('#detail-ementa').textContent = project.ementa;
  $('#detail-facts').append(
    fact('Tipo', project.tipo), fact('Data de apresentação', formatDate(project.data_apresentacao)),
    fact('Ano de identificação', String(project.ano_identificacao)),
    fact('Situação na coleta', project.situacao_resumo), fact('Autoria resumida', project.autoria_resumo),
    fact('Identificador na Casa', project.id)
  );
  addLink($('#detail-links'), 'Abrir registro oficial', project.url_fonte, true);
  addLink($('#detail-links'), 'Abrir documento oficial', project.url_documento);
  const source = $('#detail-source');
  const filePath = projectPath(casa, ano, tipo);
  source.innerHTML = `<p>Fonte: ${HOUSES[casa]}. Este registro foi lido do arquivo público <code>${escapeHtml(filePath)}</code>, esquema v${manifest.schema_version}, gerado em ${formatTimestamp(manifest.gerado_em_utc)}.</p><p>O ano do arquivo segue a <strong>data de apresentação</strong>; o ano na identificação da proposta pode ser diferente. <a href="/dados/v1/${filePath}">Consultar JSON publicado</a>.</p>`;
  const limits = $('#detail-limits');
  const missing = casa === 'camara'
    ? 'A exportação atual da Câmara não inclui situação resumida, autoria detalhada ou URL de documento neste registro.'
    : 'Situação e autoria resumidas representam os campos disponíveis na coleta; valores vazios permanecem não informados.';
  limits.innerHTML = `<p>${missing}</p><p>Tramitações, votações vinculadas, temas, texto integral processado e classificações enriquecidas não fazem parte do JSON v1. A falta de um vínculo neste painel não demonstra que o evento não ocorreu.</p><p>Indicadores ainda não publicados: ${escapeHtml(coverage.indicadores_nao_publicados.join(', '))}. Veja a <a href="/metodologia.html">metodologia</a>.</p>`;
  initTabs(document);
  $('#detail-content').hidden = false;
  setState(state, '');
} catch (error) {
  setState(state, error.message, 'error');
}
