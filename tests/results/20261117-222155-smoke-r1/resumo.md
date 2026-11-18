# Resumo — smoke (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Verificar /health, /instance e /work no ambiente implantado |
| Responsável | Pessoa 1 |
| Ambiente | aws |
| Região | us-east-2 |
| Imagem | api-189bf27 |
| Task definition | arn:aws:ecs:us-east-2:7795****9628:task-definition/richard-strauss-api:2 |
| Início / fim (UTC) | 2026-11-17T22:22:07.936Z / 2026-11-17T22:22:11.148Z |
| Capacidade de 1 task usada (req/s) | — |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 10 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 3 | 0 | 0.934 | 656.9 | 738.4 | 738.4 | 0 |

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| — | — | — |

média dos datapoints de 1 min do serviço (média entre as tasks).

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T22:17:56.549Z | ecs | (service richard-strauss-api) has started 1 tasks: (task 3fc5bd8bd27f49578bf8f5fd0fe7c1bc). |
| 2026-11-17T22:18:05.994Z | ecs | (service richard-strauss-api) has started 2 tasks: (task 446ef2ab351d4c8884d03fdea5101518) (task 6c471c822df04494b4d224b67d4ea0b5). |
| 2026-11-17T22:18:15.498Z | ecs | (service richard-strauss-api) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T22:18:26.149Z | ecs | (service richard-strauss-api) registered 2 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T22:19:17.340Z | ecs | (service richard-strauss-api) has stopped 2 running tasks: (task 3fc5bd8bd27f49578bf8f5fd0fe7c1bc) (task 4b0b9dd188504543bbaaa344a0b3b796). |
| 2026-11-17T22:19:26.642Z | ecs | (service richard-strauss-api) deregistered 2 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T22:19:26.646Z | ecs | (service richard-strauss-api, taskSet ecs-svc/1783859276478023507) has begun draining connections on 2 tasks. |
| 2026-11-17T22:20:19.424Z | ecs | (service richard-strauss-api) (deployment ecs-svc/2901316704708330266) deployment completed. |
| 2026-11-17T22:20:19.425Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T22:21:55.363Z | k6_inicio | k6 iniciado (smoke) |
| 2026-11-17T22:22:12.565Z | k6_fim | k6 terminou (código 0) |
