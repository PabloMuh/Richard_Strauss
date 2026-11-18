# Resumo — calibracao (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Medir a vazão máxima de uma task (CAPACIDADE_RPS) |
| Responsável | Pessoa 1 |
| Ambiente | aws |
| Região | us-east-2 |
| Imagem | api-189bf27 |
| Task definition | arn:aws:ecs:us-east-2:7795****9628:task-definition/richard-strauss-api:2 |
| Início / fim (UTC) | 2026-11-17T22:30:21.306Z / 2026-11-17T22:33:31.141Z |
| Capacidade de 1 task usada (req/s) | — |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 10 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 283 | 0 | 1.491 | 2487.3 | 3829.2 | 4782.8 | 0 |

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| 71.5 | 100 | 7 |

média dos datapoints de 1 min do serviço (média entre as tasks).

## Calibração

| Capacidade estimada pelo k6 (req/s) | Vazão estável (req/s) |
|---|---|
| 1.491 | 1.501 |

use vazao_estavel_rps (exclui os 20 s iniciais) como CAPACIDADE_RPS.

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T22:29:33.680Z | ecs | (service richard-strauss-api) has stopped 1 running tasks: (task 446ef2ab351d4c8884d03fdea5101518). |
| 2026-11-17T22:29:43.302Z | ecs | (service richard-strauss-api) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T22:29:43.306Z | ecs | (service richard-strauss-api, taskSet ecs-svc/2901316704708330266) has begun draining connections on 1 tasks. |
| 2026-11-17T22:29:43.328Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T22:30:19.929Z | k6_inicio | k6 iniciado (calibracao) |
| 2026-11-17T22:33:38.048Z | k6_fim | k6 terminou (código 0) |
