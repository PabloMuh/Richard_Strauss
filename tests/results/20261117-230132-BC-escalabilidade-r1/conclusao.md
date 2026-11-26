# Conclusão — BC-escalabilidade (repetição 1)

Revisado pela Pessoa 3 em 25/11/2026 com `resumo.md`, `timeline.csv`, `eventos.json`, `aws/autoscaling-atividades.json`, `aws/alarmes-historico.json` e as métricas de `aws/`. Horários em UTC.

## Hipótese

Em cada degrau a CPU passa de 60%, o alarme dispara e o serviço vai de 1 a 2 e de 2 a 3 tasks; sob a mesma carga, a latência cai com mais tasks. Com carga baixa, volta a 1 task após o alarme de scale-in (cerca de 15 min).

## Observação real

Em resumo, o scale-out se confirmou nos dois degraus e a latência caiu com mais tasks sob carga alta. O scale-in voltou a 1 task, mas levou cerca de 22 min, não 15. Foram 2091 requisições, 0 erros e nenhum 5XX no ALB.

### Scale-out (B)

| Degrau | Carga acima do alvo | Alarme | Decisão do Auto Scaling | Task saudável no ALB | Decisão → pronta | Carga → pronta |
|---|---|---|---|---|---|---|
| 1→2 | 23:04:12 | 23:10:50 | 23:10:50 | 23:11:25 | **35 s** | 433 s |
| 2→3 | 23:11:30 | o mesmo (continuou em ALARM) | 23:13:50 | 23:14:21 | **30 s** | 171 s |

- **1→2.** Com uma task, a CPU média ficou em 81–82% a partir do minuto 23:05. O alarme de alta precisa de 3 datapoints de 1 min acima de 60% (23:05, 23:06 e 23:07) e foi para ALARM às 23:10:50, quase 3 min depois do fim do terceiro minuto (`aws/alarmes-historico.json`). A decisão saiu 0,2 s depois do alarme.
- **2→3.** O alarme não voltou a OK entre os degraus; só voltou às 23:14:50. Terminado o cooldown de 60 s após a primeira atividade (encerrada às 23:11:58), a política pediu a 3ª task às 23:13:50 (`aws/autoscaling-atividades.json`). A análise de 17/11 media este degrau desde o primeiro alarme e mostrava 210 s. **O valor por degrau é 30 s**, da decisão até a task saudável.
- **Interpretação.** O ECS levou de 30 a 35 s da decisão até a task saudável no ALB, com pouca variação entre os degraus. A reação é dominada pela cadeia de métricas: 3 min de avaliação mais quase 3 min até o alarme mudar de estado. Por isso, no primeiro degrau, passaram cerca de 7 min (433 s) entre a carga passar do alvo e a nova task. O segundo degrau foi mais rápido de ponta a ponta (171 s) porque aproveitou o alarme que já estava em ALARM e só esperou o cooldown.

### Scale-in (C)

- A redução da carga começou às 23:19:17. O instante foi corrigido pelo ritmo do k6, que ficou 42 s atrás do plano nesse ponto.
- O alarme de baixa precisa de 15 datapoints abaixo de 54% (90% do alvo) e foi para ALARM às 23:31:45. A contagem começou ainda no degrau-2, com carga alta: a partir do minuto 23:14, as 3 tasks ficaram com 48–52% de CPU, já abaixo de 54% (`aws/alarmes-historico.json` e `aws/metricas-ecs-CPUUtilization.json`).
- Houve duas reduções:
  - **3→2 às 23:37:45**, 6 min depois do alarme. As atividades exportadas não registram o motivo dessa espera.
  - **2→1 às 23:41:45**, logo depois do fim do cooldown de 180 s, contado a partir do fim da atividade anterior (23:38:19).
- Do início da redução da carga até a primeira redução de tasks passaram **1108 s** (cerca de 18,5 min). Até ficar com 1 task, **1348 s** (cerca de 22,5 min). A política retirou uma task de cada vez, embora a CPU média da fase baixa tenha ficado em 9,6%.
- A hipótese se confirma em parte. O serviço volta a 1 task, mas em cerca de 22 min, e não em 15, por dois motivos: a espera entre o alarme e a primeira redução e a redução de uma task por vez com cooldown de 180 s.

### Mesma carga, número de tasks diferente

| Fase (carga planejada) | Tasks | Requisições | p50 (ms) | p95 (ms) | Acima de 1 s |
|---|---|---|---|---|---|
| degrau-1 (0,85 C) | 1 | 442 | 700 | 1476 | 13,1% |
| degrau-2 (1,5 C) | 2 | 353 | 728 | 1392 | 9,6% |
| degrau-2 (1,5 C) | 3 | 550 | 679 | 1074 | 6,0% |
| baixa (0,2 C) | 1 | 24 | 674 | 724 | 4,2% |
| baixa (0,2 C) | 2 | 68 | 684 | 751 | 1,5% |
| baixa (0,2 C) | 3 | 345 | 690 | 1163 | 6,4% |

- **Carga alta (degrau-2).** Com a mesma carga e a vazão acompanhando o oferecido (2,12 e 2,17 req/s, sem erros), a 3ª task reduziu o p50 em 7% e o p95 em 23%. Nesse intervalo, a CPU por task caiu de 72–74% para 48–52%. Aqui, mais tasks melhoram a latência.
- **Carga baixa.** O p50 é praticamente o mesmo com 1, 2 ou 3 tasks (674 a 690 ms), porque cada task fica ociosa a maior parte do tempo. O p95 maior com 3 tasks (1163 ms) do que com 2 (751 ms) não indica piora:
  - todas as tasks têm uma cauda de requisições acima de 1 s;
  - de 49% a 79% das lentas de cada task começam na mesma faixa de 5 s de um ciclo de 30 s, contra cerca de 17% esperados ao acaso ("Cauda de latência por task" em `resumo.md`). O ciclo coincide com o health check do container, a causa provável;
  - o p95 só cai na cauda quando mais de 5% das requisições do grupo são lentas. Isso aconteceu com 3 tasks (6,4% de 345), mas não com 2 (1 de 68).
- Em grupos de 24 e 68 requisições, uma ou duas requisições lentas mudam o p95, então o p50 é a comparação válida. Com carga baixa, mais tasks não melhoram a latência e só aumentam o custo.

## Limitações

- Uma repetição. Os tempos descrevem esta sessão, sem média nem desvio.
- O estado do serviço foi amostrado a cada 10 s. O horário de cada amostra é o início do ciclo de coleta, e o estado é lido nos segundos seguintes: a amostra que já mostra 2 tasks desejadas (23:37:44.6) tem horário 0,6 s anterior ao da decisão 3→2. As métricas do CloudWatch estão em períodos de 1 min.
- O k6 cumpriu o plano 4,3% mais devagar que o relógio (fator de 1,043). A carga efetiva foi 95,9% da planejada, e as fases terminaram mais tarde, cerca de 42 s na descida e 98 s no fim. Os instantes derivados do plano já estão corrigidos; as colunas "Planejada" mostram o plano.
- O gerador de carga roda numa máquina doméstica, e a latência inclui a rede até `us-east-2`.

## Próximos ajustes

- Se houver repetições, manter o plano e a política para que as execuções sejam comparáveis.
- Reduzir o tempo de reação exigiria outra política, por exemplo step scaling com menos períodos de avaliação. Fica como trabalho futuro e não faz parte desta entrega.
