/*
 * Gerador de carga dos experimentos (pessoa 3). Requer k6 >= 1.0.
 *
 * Cenários (variável CENARIO):
 *   smoke              verifica /health, /instance e /work (falha se algum check falhar)
 *   calibracao         satura UMA task para medir sua vazão máxima (CAPACIDADE_RPS)
 *   A-baseline         1 task, carga constante, sem Auto Scaling
 *   BC-escalabilidade  carga crescente (scale-out, B) seguida de carga baixa (scale-in, C)
 *   D-falha            2 tasks, carga constante; o orquestrador encerra 1 task no meio
 *
 * As taxas são frações de CAPACIDADE_RPS, a vazão de uma task medida no cenário calibracao.
 * Assim a mesma calibração vale para qualquer ITERACOES e para o hardware real do Fargate.
 * Procedimento completo: tests/README.md e tests/plano-de-testes.md.
 *
 * Variáveis: BASE_URL, CENARIO, CAPACIDADE_RPS, ITERACOES (0 = padrão do servidor),
 * ESCALA_TEMPO (1 = durações do plano; 0.1 = dez vezes mais rápido, só para validação),
 * VUS_MAX (300), TIMEOUT (60s), CALIBRACAO_VUS (4), RESUMO_ARQUIVO (resumo-k6.json).
 */
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import exec from 'k6/execution';

const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8080').replace(/\/+$/, '');
const CENARIO = __ENV.CENARIO || 'smoke';
const CAPACIDADE = Number(__ENV.CAPACIDADE_RPS || 0);
const ITERACOES = Number(__ENV.ITERACOES || 0);
const ESCALA = Number(__ENV.ESCALA_TEMPO || 1);
const VUS_MAX = Number(__ENV.VUS_MAX || 300);
const TIMEOUT = __ENV.TIMEOUT || '60s';
const CALIBRACAO_VUS = Number(__ENV.CALIBRACAO_VUS || 4);
const CALIBRACAO_MINUTOS = 3;
const RESUMO = __ENV.RESUMO_ARQUIVO || 'resumo-k6.json';
const URL_WORK = ITERACOES > 0 ? `${BASE_URL}/work?iterations=${ITERACOES}` : `${BASE_URL}/work`;

// Fases de cada experimento: duração em minutos (antes de ESCALA_TEMPO) e taxa oferecida
// como fração da capacidade de UMA task. Justificativa dos valores em tests/plano-de-testes.md.
// Em B a carga sobe em degraus que não passam da capacidade das tasks já existentes
// (0,85 com 1 task; 1,5 depois do 1º scale-out), para não acumular fila nem gerar timeouts.
export const PLANOS = {
  'A-baseline': [{ fase: 'constante', minutos: 5, de: 0.5, ate: 0.5 }],
  'BC-escalabilidade': [
    { fase: 'aquecimento', minutos: 2, de: 0.3, ate: 0.3 },
    { fase: 'subida-1', minutos: 1, de: 0.3, ate: 0.85 },
    { fase: 'degrau-1', minutos: 6, de: 0.85, ate: 0.85 },
    { fase: 'subida-2', minutos: 1, de: 0.85, ate: 1.5 },
    { fase: 'degrau-2', minutos: 7, de: 1.5, ate: 1.5 },
    { fase: 'descida', minutos: 1, de: 1.5, ate: 0.2 },
    { fase: 'baixa', minutos: 22, de: 0.2, ate: 0.2 },
  ],
  'D-falha': [{ fase: 'constante', minutos: 10, de: 0.8, ate: 0.8 }],
};

if (!(ESCALA > 0 && ESCALA <= 1)) throw new Error('ESCALA_TEMPO deve estar em (0, 1].');

const segundos = (minutos) => Math.max(1, Math.round(minutos * 60 * ESCALA));
const porMinuto = (fracao) => Math.max(1, Math.round(fracao * CAPACIDADE * 60));
const respostas = new Counter('respostas_por_instancia');

function planoAbsoluto() {
  let inicio = 0;
  return (PLANOS[CENARIO] || []).map((p) => {
    const duracao = segundos(p.minutos);
    const item = {
      fase: p.fase, inicio_s: inicio, fim_s: inicio + duracao,
      taxa_inicial_rps: porMinuto(p.de) / 60, taxa_final_rps: porMinuto(p.ate) / 60,
      fracao_inicial: p.de, fracao_final: p.ate,
    };
    inicio += duracao;
    return item;
  });
}

function construirCenarios() {
  if (CENARIO === 'smoke') {
    return { smoke: { executor: 'per-vu-iterations', vus: 1, iterations: 3, maxDuration: '2m', exec: 'smoke' } };
  }
  if (CENARIO === 'calibracao') {
    return { calibracao: { executor: 'constant-vus', vus: CALIBRACAO_VUS, duration: `${segundos(CALIBRACAO_MINUTOS)}s`, exec: 'trabalho' } };
  }
  const plano = PLANOS[CENARIO];
  if (!plano) throw new Error(`CENARIO desconhecido: ${CENARIO}`);
  if (!(CAPACIDADE > 0)) throw new Error('Informe CAPACIDADE_RPS (req/s de UMA task), medida no cenário calibracao.');
  plano.forEach((p, i) => {
    if (i > 0 && plano[i - 1].ate !== p.de) throw new Error(`Fases descontínuas em ${CENARIO}: ${plano[i - 1].fase} -> ${p.fase}`);
  });
  const pico = Math.max(...plano.map((p) => Math.max(p.de, p.ate))) * CAPACIDADE;
  return {
    [CENARIO]: {
      executor: 'ramping-arrival-rate',
      startRate: porMinuto(plano[0].de),
      timeUnit: '1m',
      preAllocatedVUs: Math.min(VUS_MAX, Math.max(5, Math.ceil(pico * 5))),
      maxVUs: VUS_MAX,
      stages: plano.map((p) => ({ target: porMinuto(p.ate), duration: `${segundos(p.minutos)}s` })),
      exec: 'trabalho',
    },
  };
}

export const options = {
  scenarios: construirCenarios(),
  thresholds: CENARIO === 'smoke' ? { checks: ['rate==1'] } : {},
  dns: { ttl: '30s', select: 'random', policy: 'preferIPv4' },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const LIMITES = planoAbsoluto();

function faseAtual() {
  if (!LIMITES.length) return CENARIO;
  const decorrido = (Date.now() - exec.scenario.startTime) / 1000;
  const atual = LIMITES.find((l) => decorrido < l.fim_s);
  return atual ? atual.fase : LIMITES[LIMITES.length - 1].fase;
}

function campo(res, caminho) {
  try { return res.json(caminho); } catch (e) { return undefined; }
}

// Sem o header x-instance-id, a resposta veio do balanceador (ex.: 502/503/504 do ALB) e não de uma task.
function instancia(res) {
  return res.headers['X-Instance-Id'] || (res.status === 0 ? 'sem-resposta' : 'balanceador');
}

export function setup() {
  return { inicio_utc: new Date().toISOString() };
}

export function trabalho() {
  const fase = faseAtual();
  const res = http.get(URL_WORK, { tags: { name: 'work', fase }, timeout: TIMEOUT, responseType: 'none' });
  respostas.add(1, { instancia: instancia(res), fase });
  check(res, { 'work 200': (r) => r.status === 200 }, { fase });
}

export function smoke() {
  const health = http.get(`${BASE_URL}/health`, { tags: { name: 'health' } });
  check(health, { 'health 200 e status ok': (r) => r.status === 200 && campo(r, 'status') === 'ok' });
  const inst = http.get(`${BASE_URL}/instance`, { tags: { name: 'instance' } });
  check(inst, { 'instance_id presente': (r) => r.status === 200 && String(campo(r, 'instance_id') || '').length > 0 });
  const work = http.get(URL_WORK, { tags: { name: 'work', fase: 'smoke' }, timeout: TIMEOUT });
  check(work, { 'work 200 com digest': (r) => r.status === 200 && String(campo(r, 'digest') || '').length === 64 });
  respostas.add(1, { instancia: instancia(work), fase: 'smoke' });
}

function valor(data, metrica, chave) {
  const m = data.metrics[metrica];
  return m && m.values && m.values[chave] !== undefined ? m.values[chave] : null;
}

export function handleSummary(data) {
  const duracaoS = data.state.testRunDurationMs / 1000;
  const requisicoes = valor(data, 'http_reqs', 'count') || 0;
  const resumo = {
    cenario: CENARIO,
    base_url: BASE_URL,
    capacidade_rps: CAPACIDADE || null,
    iteracoes: ITERACOES || null,
    escala_tempo: ESCALA,
    timeout: TIMEOUT,
    plano: planoAbsoluto(),
    inicio_utc: data.setup_data ? data.setup_data.inicio_utc : null,
    fim_utc: new Date().toISOString(),
    duracao_s: duracaoS,
    requisicoes,
    vazao_media_rps: valor(data, 'http_reqs', 'rate'),
    taxa_falhas: valor(data, 'http_req_failed', 'rate'),
    taxa_checks: valor(data, 'checks', 'rate'),
    iteracoes_descartadas: valor(data, 'dropped_iterations', 'count') || 0,
    vus_max: valor(data, 'vus_max', 'max'),
    latencia_ms: data.metrics.http_req_duration ? data.metrics.http_req_duration.values : null,
  };
  if (CENARIO === 'calibracao') {
    // Pedidos que terminaram dentro da janela / duração: com a fila sempre cheia, é a vazão máxima da task.
    resumo.capacidade_estimada_rps = requisicoes / duracaoS;
  }
  const linhas = [
    '',
    `Cenário ${CENARIO} contra ${BASE_URL}: ${requisicoes} requisições em ${duracaoS.toFixed(1)} s`,
    `  vazão média ${(resumo.vazao_media_rps || 0).toFixed(2)} req/s | falhas ${((resumo.taxa_falhas || 0) * 100).toFixed(2)}%` +
      ` | p95 ${resumo.latencia_ms ? resumo.latencia_ms['p(95)'].toFixed(0) : '-'} ms | iterações descartadas ${resumo.iteracoes_descartadas}`,
  ];
  if (resumo.taxa_checks !== null) linhas.push(`  checks aprovados: ${(resumo.taxa_checks * 100).toFixed(1)}%`);
  if (resumo.capacidade_estimada_rps) linhas.push(`  CAPACIDADE_RPS estimada de 1 task: ${resumo.capacidade_estimada_rps.toFixed(2)} req/s`);
  linhas.push(`  resumo: ${RESUMO}`, '');
  return { [RESUMO]: JSON.stringify(resumo, null, 2), stdout: linhas.join('\n') };
}
