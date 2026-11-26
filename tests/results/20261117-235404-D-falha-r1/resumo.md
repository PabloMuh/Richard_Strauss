# Resumo — D-falha (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | Encerrar 1 de 2 tasks sob 80% da capacidade de uma task |
| Responsável | Pessoa 1 |
| Ambiente | aws |
| Região | us-east-2 |
| Imagem | api-62f1e8e |
| Task definition | arn:aws:ecs:us-east-2:7795****9628:task-definition/richard-strauss-api:3 |
| Início / fim (UTC) | 2026-11-17T23:54:05.940Z / 2026-11-18T00:04:30.797Z |
| Capacidade de 1 task usada (req/s) | 1.5 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 10 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 720 | 0 | 1.152 | 690.5 | 1106.3 | 2067.6 | 0 |

**Ritmo do k6:** as iterações do plano começaram em início + 0.43 s + 1.042 × horário previsto (resíduo máximo de 0.8 s). A carga efetiva foi 96% da planejada e as fases terminaram mais tarde no relógio real. As colunas "Planejada" mostram o plano; os instantes derivados dele (carga acima do alvo, redução da carga) já estão corrigidos pelo ritmo. As fases das requisições seguem o relógio real, por isso o começo de cada fase ainda recebe a taxa da fase anterior.

## Por fase

| Fase | Duração (s) | Planejada (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | > 1 s (%) | CPU média (%) | Respostas por instância |
|---|---|---|---|---|---|---|---|---|---|
| constante | 624.9 | 1.2 | 1.152 | 0 | 690.5 | 1106.3 | 5.8 | 39.8 | 09a50126dad74b90a260f6f7308f2772: 127, c6767d66ff724c3e8a9a6f74849e5130: 214, dafbb3464774400295b1fc1f38890670: 379 |

CPU média da fase: datapoints de 1 min do CloudWatch inteiramente dentro da fase (— quando a fase não contém um minuto inteiro).

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| 39.8 | 76.1 | 6.9 |

médias dos datapoints de 1 min do serviço (média entre as tasks) inteiramente dentro da janela do k6; a máxima considera também os minutos das bordas.

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Planejada (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | > 1 s (%) |
|---|---|---|---|---|---|---|---|---|---|
| constante | 1.2 | 1 | 31.4 | 36 | 1.148 | 0 | 706.7 | 1709.8 | 13.9 |
| constante | 1.2 | 2 | 593.5 | 684 | 1.153 | 0 | 689.2 | 1082.4 | 5.4 |

Quando a coluna "> 1 s" fica perto de 5%, poucas requisições decidem se o p95 cai na cauda; em grupos pequenos, compare também o p50.

## Cauda de latência por task

Requisições acima de 1000 ms por task e quantas começam na mesma faixa de 5 s de um ciclo de 30 s (intervalo do health check do container). Sem causa periódica, a faixa mais densa reuniria cerca de 16.7% das lentas.

| Task | Requisições | Lentas | Lentas (%) | Lentas na faixa mais densa | Na faixa (%) | Início da faixa no ciclo (s) |
|---|---|---|---|---|---|---|
| 09a50126dad74b90a260f6f7308f2772 | 127 | 8 | 6.3 | 5 | 62.5 | 10.6 |
| c6767d66ff724c3e8a9a6f74849e5130 | 214 | 12 | 5.6 | 9 | 75 | 2.5 |
| dafbb3464774400295b1fc1f38890670 | 379 | 22 | 5.8 | 16 | 72.7 | 8.8 |

## Falha (D)

| Indicador | Valor |
|---|---|
| Task encerrada | 09a50126dad74b90a260f6f7308f2772 |
| Parada | 2026-11-17T23:57:10.813Z |
| Queda observada (alvos saudáveis abaixo de antes) | 2026-11-17T23:57:47.510Z |
| Substituta vista | 2026-11-17T23:57:47.510Z |
| Recuperada (saudáveis como antes) | 2026-11-17T23:58:18.880Z |
| Tempo até a queda (s) | 37 |
| Tempo até a substituta (s) | 37 |
| Tempo de recuperação (s) | 68 |
| Erros na janela da falha | 0 de 119 |

| Período | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|
| 60 s antes | 1.15 | 0 | 711.9 | 1311.1 |
| durante | 1.161 | 0 | 701.8 | 1659.4 |
| depois (+30 s) | 1.155 | 0 | 682.1 | 1084.3 |

Tempos medidos a partir do estado amostrado a cada 10 s.

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T23:52:54.414Z | ecs | (service richard-strauss-api) has started 1 tasks: (task 09a50126dad74b90a260f6f7308f2772). |
| 2026-11-17T23:53:22.105Z | ecs | (service richard-strauss-api) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:54:00.687Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-17T23:54:04.765Z | k6_inicio | k6 iniciado (D-falha) |
| 2026-11-17T23:57:10.813Z | stop_task | Task 09a50126dad74b90a260f6f7308f2772 encerrada com stop-task |
| 2026-11-17T23:57:47.281Z | ecs | (service richard-strauss-api) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:57:47.284Z | ecs | (service richard-strauss-api, taskSet ecs-svc/0316170514152323679) has begun draining connections on 1 tasks. |
| 2026-11-17T23:57:48.054Z | ecs | (service richard-strauss-api) has started 1 tasks: (task c6767d66ff724c3e8a9a6f74849e5130). |
| 2026-11-17T23:58:16.900Z | ecs | (service richard-strauss-api) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-2:7795****9628:targetgroup/richard-strauss-api/80c6de7f6ffd80f5) |
| 2026-11-17T23:58:55.753Z | ecs | (service richard-strauss-api) has reached a steady state. |
| 2026-11-18T00:04:32.496Z | k6_fim | k6 terminou (código 0) |
