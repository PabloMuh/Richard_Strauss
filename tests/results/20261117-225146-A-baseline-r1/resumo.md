# Resumo — A-baseline (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Linha de base: 1 task, carga constante de 50% da capacidade, sem Auto Scaling |
| Responsável | Pessoa 1 |
| Ambiente | aws |
| Região | us-east-2 |
| Imagem | api-62f1e8e |
| Task definition | arn:aws:ecs:us-east-2:7795****9628:task-definition/richard-strauss-api:3 |
| Início / fim (UTC) | 2026-11-17T22:51:46.890Z / 2026-11-17T22:57:00.394Z |
| Capacidade de 1 task usada (req/s) | 1.5 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 10 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 225 | 0 | 0.718 | 660.1 | 1014.4 | 2041 | 0 |

## Por fase

| Fase | Duração (s) | Oferecida (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | Respostas por instância |
|---|---|---|---|---|---|---|---|
| constante | 300 | 0.75 | 0.75 | 0 | 660.1 | 1014.4 | 5dfa3b11c57345a39d286da496616b7a: 225 |

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| 37.7 | 58.1 | 7 |

média dos datapoints de 1 min do serviço (média entre as tasks).

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Oferecida (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| constante | 0.75 | 1 | 300 | 215 | 0.717 | 0 | 660.1 | 1038.2 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T22:48:43.631Z | ecs | (service richard-strauss-api) has started 1 tasks: (task 5dfa3b11c57345a39d286da496616b7a). |
| 2026-11-17T22:49:13.953Z | ecs | (service richard-strauss-api) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T22:49:54.548Z | ecs | (service richard-strauss-api) has stopped 1 running tasks: (task 6c471c822df04494b4d224b67d4ea0b5). |
| 2026-11-17T22:50:04.864Z | ecs | (service richard-strauss-api) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T22:50:04.867Z | ecs | (service richard-strauss-api, taskSet ecs-svc/2901316704708330266) has begun draining connections on 1 tasks. |
| 2026-11-17T22:51:06.454Z | ecs | (service richard-strauss-api) (deployment ecs-svc/0316170514152323679) deployment completed. |
| 2026-11-17T22:51:06.455Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T22:51:46.108Z | k6_inicio | k6 iniciado (A-baseline) |
| 2026-11-17T22:57:05.752Z | k6_fim | k6 terminou (código 0) |
