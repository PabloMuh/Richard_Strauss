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

**Ritmo do k6:** as iterações do plano começaram em início + 1.63 s + 1.04 × horário previsto (resíduo máximo de 0.77 s). A carga efetiva foi 96.1% da planejada e as fases terminaram mais tarde no relógio real. As colunas "Planejada" mostram o plano; os instantes derivados dele (carga acima do alvo, redução da carga) já estão corrigidos pelo ritmo. As fases das requisições seguem o relógio real, por isso o começo de cada fase ainda recebe a taxa da fase anterior.

## Por fase

| Fase | Duração (s) | Planejada (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | > 1 s (%) | CPU média (%) | Respostas por instância |
|---|---|---|---|---|---|---|---|---|---|
| constante | 312.4 | 0.75 | 0.717 | 0.444 | 695.7 | 942 | 4.5 | 49.1 | 6c471c822df04494b4d224b67d4ea0b5: 224, balanceador: 1 |

CPU média da fase: datapoints de 1 min do CloudWatch inteiramente dentro da fase (— quando a fase não contém um minuto inteiro).

## CPU e memória (CloudWatch)

| CPU média (%) | CPU máxima (%) | Memória média (%) |
|---|---|---|
| 49.1 | 59.4 | 7 |

médias dos datapoints de 1 min do serviço (média entre as tasks) inteiramente dentro da janela do k6; a máxima considera também os minutos das bordas.

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Planejada (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | > 1 s (%) |
|---|---|---|---|---|---|---|---|---|---|
| constante | 0.75 | 1 | 312.4 | 225 | 0.717 | 0.444 | 695.7 | 942 | 4.5 |

Quando a coluna "> 1 s" fica perto de 5%, poucas requisições decidem se o p95 cai na cauda; em grupos pequenos, compare também o p50.

## Cauda de latência por task

Requisições acima de 1000 ms por task e quantas começam na mesma faixa de 5 s de um ciclo de 30 s (intervalo do health check do container). Sem causa periódica, a faixa mais densa reuniria cerca de 16.7% das lentas.

| Task | Requisições | Lentas | Lentas (%) | Lentas na faixa mais densa | Na faixa (%) | Início da faixa no ciclo (s) |
|---|---|---|---|---|---|---|
| 6c471c822df04494b4d224b67d4ea0b5 | 224 | 10 | 4.5 | 8 | 80 | 21.3 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-17T22:37:42.686Z | k6_inicio | k6 iniciado (A-baseline) |
| 2026-11-17T22:43:03.392Z | k6_fim | k6 terminou (código 0) |
