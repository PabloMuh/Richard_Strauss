# Resumo — A-baseline (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Linha de base: 1 task, carga constante de 50% da capacidade, sem Auto Scaling |
| Responsável | Pessoa 1 |
| Ambiente | aws |
| Região | us-east-2 |
| Imagem | api-189bf27 |
| Task definition | arn:aws:ecs:us-east-2:7795****9628:task-definition/richard-strauss-api:2 |
| Início / fim (UTC) | 2026-11-17T22:37:43.579Z / 2026-11-17T22:42:56.004Z |
| Capacidade de 1 task usada (req/s) | 1.5 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 10 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 225 | 0.444 | 0.717 | 695.7 | 942 | 2026.9 | 0 |

## Por fase

| Fase | Duração (s) | Oferecida (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | Respostas por instância |
|---|---|---|---|---|---|---|---|
| constante | 300 | 0.75 | 0.747 | 0.444 | 695.7 | 942 | 6c471c822df04494b4d224b67d4ea0b5: 224, balanceador: 1 |

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| 41.2 | 59.4 | 7 |

média dos datapoints de 1 min do serviço (média entre as tasks).

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Oferecida (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| constante | 0.75 | 1 | 300 | 215 | 0.713 | 0.465 | 695.7 | 942 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T22:37:42.686Z | k6_inicio | k6 iniciado (A-baseline) |
| 2026-11-17T22:43:03.392Z | k6_fim | k6 terminou (código 0) |
