# Resumo — BC-escalabilidade (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | B: scale-out com carga em degraus (85% e 150% da capacidade de uma task); C: scale-in após reduzir a carga para 20% |
| Responsável | Pessoa 1 |
| Ambiente | aws |
| Região | us-east-2 |
| Imagem | api-62f1e8e |
| Task definition | arn:aws:ecs:us-east-2:7795****9628:task-definition/richard-strauss-api:3 |
| Início / fim (UTC) | 2026-11-17T23:01:34.225Z / 2026-11-17T23:43:12.387Z |
| Capacidade de 1 task usada (req/s) | 1.5 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | {"min": 1, "max": 3, "targetCpu": 60.0, "scaleOutCooldown": 60, "scaleInCooldown": 180, "policyName": "richard-strauss-cpu"} |
| Coleta do estado (s) | 10 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 2091 | 0 | 0.837 | 692.4 | 1300.6 | 2074.7 | 0 |

## Por fase

| Fase | Duração (s) | Oferecida (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | Respostas por instância |
|---|---|---|---|---|---|---|---|
| aquecimento | 120 | 0.45 | 0.433 | 0 | 691.5 | 809.8 | 5dfa3b11c57345a39d286da496616b7a: 52 |
| subida-1 | 60 | 0.867 | 0.767 | 0 | 700.9 | 1393.7 | 5dfa3b11c57345a39d286da496616b7a: 46 |
| degrau-1 | 360 | 1.283 | 1.231 | 0 | 700.3 | 1476 | 5dfa3b11c57345a39d286da496616b7a: 443 |
| subida-2 | 60 | 1.767 | 1.417 | 0 | 722.8 | 1691.5 | 24fb3e4deba1470bbe0480e29d1fe4bc: 8, 5dfa3b11c57345a39d286da496616b7a: 77 |
| degrau-2 | 420 | 2.25 | 2.155 | 0 | 691.9 | 1147.2 | 24fb3e4deba1470bbe0480e29d1fe4bc: 362, 5dfa3b11c57345a39d286da496616b7a: 362, dafbb3464774400295b1fc1f38890670: 181 |
| descida | 60 | 1.275 | 2.05 | 0 | 669.7 | 1465.5 | 24fb3e4deba1470bbe0480e29d1fe4bc: 40, 5dfa3b11c57345a39d286da496616b7a: 41, dafbb3464774400295b1fc1f38890670: 42 |
| baixa | 1320 | 0.3 | 0.331 | 0 | 688.5 | 1149.2 | 24fb3e4deba1470bbe0480e29d1fe4bc: 151, 5dfa3b11c57345a39d286da496616b7a: 116, dafbb3464774400295b1fc1f38890670: 170 |

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| 31.3 | 94.8 | 7 |

média dos datapoints de 1 min do serviço (média entre as tasks).

## Scale-out (B)

Máximo de tasks: 3; final: 1. "Carga acima do alvo" é o momento em que a carga oferecida passa da CPU-alvo para as tasks existentes antes do degrau.

| Degrau | Carga acima do alvo | Alarme | Decisão | Task pronta | Alarme→pronta (s) | Decisão→pronta (s) | Carga→pronta (s) |
|---|---|---|---|---|---|---|---|
| 1→2 | 2026-11-17T23:04:06.952Z | 2026-11-17T23:10:50.326Z | 2026-11-17T23:10:50.490Z | 2026-11-17T23:11:25.343Z | 35 | 35 | 438 |
| 2→3 | 2026-11-17T23:11:06.532Z | 2026-11-17T23:10:50.326Z | 2026-11-17T23:10:50.490Z | 2026-11-17T23:14:20.630Z | 210 | 210 | 194 |

## Scale-in (C)

Carga reduzida em 2026-11-17T23:18:34.225Z.

| Degrau | Alarme | Decisão | Desejadas reduzidas | Redução da carga→scale-in (s) | Alarme→scale-in (s) |
|---|---|---|---|---|---|
| 3→2 | 2026-11-17T23:31:45.088Z | — | 2026-11-17T23:37:44.648Z | 1150 | 360 |
| 2→1 | 2026-11-17T23:31:45.088Z | 2026-11-17T23:37:45.235Z | 2026-11-17T23:41:51.630Z | 1397 | 607 |

Tempos medidos a partir do estado amostrado a cada 10 s (resolução da medição).

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Oferecida (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| aquecimento | 0.45 | 1 | 120 | 51 | 0.425 | 0 | 691.5 | 809.8 |
| degrau-1 | 1.283 | 1 | 360 | 442 | 1.228 | 0 | 700.2 | 1476 |
| degrau-2 | 2.25 | 2 | 166.4 | 353 | 2.121 | 0 | 727.7 | 1391.8 |
| degrau-2 | 2.25 | 3 | 253.6 | 550 | 2.169 | 0 | 678.7 | 1074.2 |
| baixa | 0.3 | 2 | 219.6 | 63 | 0.287 | 0 | 684.3 | 750.7 |
| baixa | 0.3 | 3 | 1100.4 | 345 | 0.314 | 0 | 689.8 | 1163.3 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T23:01:32.496Z | k6_inicio | k6 iniciado (BC-escalabilidade) |
| 2026-11-17T23:01:50.324Z | alarme | Alarme de alta (scale-out): Alarm updated from INSUFFICIENT_DATA to OK |
| 2026-11-17T23:02:45.089Z | alarme | Alarme de baixa (scale-in): Alarm updated from INSUFFICIENT_DATA to ALARM |
| 2026-11-17T23:07:45.087Z | alarme | Alarme de baixa (scale-in): Alarm updated from ALARM to OK |
| 2026-11-17T23:10:50.326Z | alarme | Alarme de alta (scale-out): Alarm updated from OK to ALARM |
| 2026-11-17T23:10:50.490Z | escalonamento | Setting desired count to 2. |
| 2026-11-17T23:10:55.134Z | ecs | (service richard-strauss-api) has started 1 tasks: (task 24fb3e4deba1470bbe0480e29d1fe4bc). |
| 2026-11-17T23:11:24.091Z | ecs | (service richard-strauss-api) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:12:02.124Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T23:13:50.494Z | escalonamento | Setting desired count to 3. |
| 2026-11-17T23:13:53.286Z | ecs | (service richard-strauss-api) has started 1 tasks: (task dafbb3464774400295b1fc1f38890670). |
| 2026-11-17T23:14:21.548Z | ecs | (service richard-strauss-api) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:14:50.326Z | alarme | Alarme de alta (scale-out): Alarm updated from ALARM to OK |
| 2026-11-17T23:14:59.780Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T23:31:45.088Z | alarme | Alarme de baixa (scale-in): Alarm updated from OK to ALARM |
| 2026-11-17T23:37:45.235Z | escalonamento | Setting desired count to 2. |
| 2026-11-17T23:37:49.890Z | ecs | (service richard-strauss-api) has stopped 1 running tasks: (task 5dfa3b11c57345a39d286da496616b7a). |
| 2026-11-17T23:37:59.795Z | ecs | (service richard-strauss-api) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:37:59.799Z | ecs | (service richard-strauss-api, taskSet ecs-svc/0316170514152323679) has begun draining connections on 1 tasks. |
| 2026-11-17T23:37:59.877Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T23:41:45.265Z | escalonamento | Setting desired count to 1. |
| 2026-11-17T23:41:45.859Z | ecs | (service richard-strauss-api) has stopped 1 running tasks: (task 24fb3e4deba1470bbe0480e29d1fe4bc). |
| 2026-11-17T23:41:55.482Z | ecs | (service richard-strauss-api) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:41:55.486Z | ecs | (service richard-strauss-api, taskSet ecs-svc/0316170514152323679) has begun draining connections on 1 tasks. |
| 2026-11-17T23:41:55.560Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T23:43:17.125Z | k6_fim | k6 terminou (código 0) |
