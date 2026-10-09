const BASE = '/dados/v1/';
const requests = new Map();

export const HOUSES = { camara: 'Câmara', senado: 'Senado' };
export const TYPES = ['PL', 'PLP', 'PEC'];

export function fetchData(path) {
  if (!/^[a-z0-9_./-]+\.json$/i.test(path) || path.includes('..')) {
    return Promise.reject(new Error('Caminho de dados inválido.'));
  }
  if (!requests.has(path)) {
    const request = fetch(BASE + path, { cache: 'no-cache' })
      .then(response => {
        if (!response.ok) throw new Error(`Arquivo indisponível (${response.status}): ${path}`);
        return response.json();
      })
      .then(json => {
        const version = json.schema_version ?? json.meta?.schema_version;
        if (version !== 1) throw new Error(`Versão de dados incompatível: ${path}`);
        return json;
      })
      .catch(error => { requests.delete(path); throw error; });
    requests.set(path, request);
  }
  return requests.get(path);
}

export function loadManifest() { return fetchData('manifesto.json'); }
export function loadCoverage() { return fetchData('cobertura.json'); }
export function loadIndicator(name) { return fetchData(`indicadores/${name}.json`); }
export function loadPeople(casa) {
  if (!(casa in HOUSES)) return Promise.reject(new Error('Casa inválida.'));
  return fetchData(`parlamentares/${casa}/atuais.json`);
}
export function projectPath(casa, ano, tipo) {
  if (!(casa in HOUSES) || !Number.isInteger(Number(ano)) || !TYPES.includes(tipo)) throw new Error('Recorte de projetos inválido.');
  return `projetos/${casa}/${ano}/${tipo.toLowerCase()}.json`;
}
export function loadProjects(casa, ano, tipo) { return fetchData(projectPath(casa, ano, tipo)); }
export function availableYears(manifest) {
  return [...new Set(manifest.arquivos.map(item => /^projetos\/(?:camara|senado)\/(\d{4})\/(?:pl|plp|pec)\.json$/.exec(item.caminho)?.[1]).filter(Boolean))].map(Number).sort((a, b) => b - a);
}
export function availablePartitions(manifest, house, year, type) {
  const entries = manifest.arquivos.filter(item => {
    const match = /^projetos\/(camara|senado)\/(\d{4})\/(pl|plp|pec)\.json$/.exec(item.caminho);
    return match && (house === 'todas' || match[1] === house) && (year === 'todos' || Number(match[2]) === Number(year)) && (type === 'todos' || match[3].toUpperCase() === type);
  });
  return entries.map(item => item.caminho);
}
export async function loadPartitions(paths, onProgress, concurrency = 4) {
  const result = new Array(paths.length);
  let cursor = 0;
  let done = 0;
  const workers = Array.from({ length: Math.min(concurrency, paths.length) }, async () => {
    while (cursor < paths.length) {
      const index = cursor++;
      result[index] = await fetchData(paths[index]);
      done += 1;
      onProgress?.(done, paths.length);
    }
  });
  await Promise.all(workers);
  return result.flatMap(file => file.dados);
}

export function projectUrl(project) {
  const params = new URLSearchParams({ casa: project.casa, ano: project.data_apresentacao.slice(0, 4), tipo: project.tipo, id: project.id });
  return `/projeto.html?${params}`;
}
export function explorerUrl({ casa, ano, tipo, mes } = {}) {
  const params = new URLSearchParams();
  if (casa && casa !== 'todas') params.set('casa', casa);
  if (ano && ano !== 'todos') params.set('ano', ano);
  if (tipo && tipo !== 'todos') params.set('tipo', tipo);
  if (mes && mes !== 'todos') params.set('mes', mes);
  return `/projetos.html${params.size ? '?' + params : ''}`;
}
