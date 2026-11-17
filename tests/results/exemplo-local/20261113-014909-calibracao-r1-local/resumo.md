# Resumo — calibracao (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Medir a vazão máxima de uma task (CAPACIDADE_RPS) |
| Responsável | leonardo-lbp |
| Ambiente | local |
| Região | — |
| Imagem | — |
| Task definition | — |
| Início / fim (UTC) | 2026-11-13T01:49:12.279Z / 2026-11-13T01:50:43.762Z |
| Capacidade de 1 task usada (req/s) | — |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 0.5 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 5 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 159 | 0 | 1.738 | 1995.1 | 3890.6 | 7109 | 0 |

## Calibração

| Capacidade estimada pelo k6 (req/s) | Vazão estável (req/s) |
|---|---|
| 1.738 | 1.749 |

use vazao_estavel_rps (exclui os 20 s iniciais) como CAPACIDADE_RPS.

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-13T01:49:09.720Z | k6_inicio | k6 iniciado (calibracao) |
| 2026-11-13T01:50:44.942Z | k6_fim | k6 terminou (código 0) |
