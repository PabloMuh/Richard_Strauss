# Resumo — smoke (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Verificar /health, /instance e /work no ambiente implantado |
| Responsável | leonardo-lbp |
| Ambiente | local |
| Região | — |
| Imagem | — |
| Task definition | — |
| Início / fim (UTC) | 2026-11-13T01:48:31.829Z / 2026-11-13T01:48:33.155Z |
| Capacidade de 1 task usada (req/s) | — |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 5 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 3 | 0 | 2.262 | 401.7 | 500 | 500 | 0 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-13T01:48:30.851Z | k6_inicio | k6 iniciado (smoke) |
| 2026-11-13T01:48:34.951Z | k6_fim | k6 terminou (código 0) |
