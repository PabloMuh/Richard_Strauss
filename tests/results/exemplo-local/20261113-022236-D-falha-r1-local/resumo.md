# Resumo — D-falha (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Encerrar 1 de 2 tasks sob 80% da capacidade de uma task |
| Responsável | leonardo-lbp |
| Ambiente | local |
| Região | — |
| Imagem | — |
| Task definition | — |
| Início / fim (UTC) | 2026-11-13T02:22:36.929Z / 2026-11-13T02:25:36.931Z |
| Capacidade de 1 task usada (req/s) | 1.749 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 0.3 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 5 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 251 | 0.797 | 1.383 | 297.5 | 479.2 | 695.2 | 0 |

## Por fase

| Fase | Duração (s) | Oferecida (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | Respostas por instância |
|---|---|---|---|---|---|---|---|
| constante | 180 | 1.4 | 1.383 | 0.797 | 297.5 | 479.2 | balanceador: 2, local-1: 105, local-2: 144 |

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Oferecida (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| constante | 1.4 | 1 | 30.1 | 42 | 1.397 | 0 | 306.4 | 479.2 |
| constante | 1.4 | 2 | 149.9 | 209 | 1.381 | 0.957 | 295.3 | 451.5 |

## Falha (D)

| Indicador | Valor |
|---|---|
| Task encerrada | api-1 |
| Parada | 2026-11-13T02:23:31.830Z |
| Queda observada | 2026-11-13T02:23:36.519Z |
| Substituta vista | 2026-11-13T02:23:56.876Z |
| Recuperada (saudáveis como antes) | 2026-11-13T02:24:06.583Z |
| Tempo até a substituta (s) | 25 |
| Tempo de recuperação (s) | 35 |
| Erros na janela da falha | 2 de 98 |

| Período | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|
| 60 s antes | 1.267 | 0 | 304.7 | 549.9 |
| durante | 1.352 | 4.082 | 305.8 | 479.2 |
| depois (+30 s) | 1.401 | 0 | 287.1 | 414.2 |

Tempos medidos a partir do estado amostrado a cada 5 s.

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-13T02:22:36.368Z | k6_inicio | k6 iniciado (D-falha) |
| 2026-11-13T02:23:31.830Z | stop_task | Réplica api-1 encerrada (docker compose stop) |
| 2026-11-13T02:23:56.876Z | start_replica | Réplica api-1 reiniciada após 20 s (no ECS a substituição é automática) |
| 2026-11-13T02:25:37.937Z | k6_fim | k6 terminou (código 0) |
