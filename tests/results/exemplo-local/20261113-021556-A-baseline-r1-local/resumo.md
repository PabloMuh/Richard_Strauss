# Resumo — A-baseline (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Linha de base: 1 task, carga constante de 50% da capacidade, sem Auto Scaling |
| Responsável | leonardo-lbp |
| Ambiente | local |
| Região | — |
| Imagem | — |
| Task definition | — |
| Início / fim (UTC) | 2026-11-13T02:15:56.925Z / 2026-11-13T02:17:26.931Z |
| Capacidade de 1 task usada (req/s) | 1.749 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 0.3 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 5 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 77 | 0 | 0.855 | 276.9 | 330.6 | 621.3 | 0 |

## Por fase

| Fase | Duração (s) | Oferecida (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | Respostas por instância |
|---|---|---|---|---|---|---|---|
| constante | 90 | 0.867 | 0.856 | 0 | 276.9 | 330.6 | local-1: 77 |

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Oferecida (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| constante | 0.867 | 1 | 90 | 77 | 0.856 | 0 | 276.9 | 330.6 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-13T02:15:56.441Z | k6_inicio | k6 iniciado (A-baseline) |
| 2026-11-13T02:17:27.873Z | k6_fim | k6 terminou (código 0) |
