# Plano de testes — pessoa 3

Experimentos que demonstram, com dados medidos, a escalabilidade e a recuperação de falhas do serviço ECS. Este plano define hipóteses, procedimentos, métricas e critérios. O passo a passo de execução está no [README](README.md).

## 1. Configuração sob teste

| Item | Valor | Origem |
|---|---|---|
| Execução | ECS com Fargate, Linux x86_64 | Plano da equipe |
| Task | 0,25 vCPU e 512 MiB; API com `WORK_CONCURRENCY=1` | `infrastructure/templates/task-definition.json` |
| Entrada | ALB (`useAlb=true`), health check em `/health` a cada 10 s, 2 acertos, drenagem de 30 s | `Provision.ps1` |
| Auto Scaling | Target tracking da CPU média do serviço; alvo 60%; mínimo 1, máximo 3 tasks; cooldown de 60 s (scale-out) e 180 s (scale-in) | `Set-AutoScaling.ps1` |
| Carga | `GET /work` (SHA-256 encadeado, CPU-bound) gerado pelo k6 em modelo aberto (taxa de chegada fixa) | `tests/load-test.js` |

O ALB é obrigatório para B, C e D: sem um endereço único, o gerador de carga não alcança as tasks criadas pelo Auto Scaling nem a task substituta.

## 2. Unidade de carga: a capacidade de uma task

O `/work` é limitado por CPU e cada task processa um cálculo por vez. Por isso, uma task tem uma vazão máxima **C** (req/s), medida no cenário `calibracao`: uma task, quatro clientes mantendo a fila sempre ocupada por 3 minutos. A CPU de uma task fica proporcional à fração de C que ela recebe.

Todas as cargas são definidas como frações de C. Assim o plano vale para o hardware real do Fargate e para qualquer `ITERACOES`, desde que a calibração use as mesmas iterações. No ambiente local (0,25 vCPU simulado no Docker), C ≈ 1,86 req/s com as 200 000 iterações padrão. **O valor no Fargate precisa ser medido**, não reaproveitado.

O target tracking ajusta o número de tasks N para manter a CPU média perto do alvo. Com carga L, a CPU média é aproximadamente L / (N·C), o que dá N ≈ L / (0,6·C).

## 3. Experimentos

| | A · Baseline | B · Scale-out | C · Scale-in | D · Falha |
|---|---|---|---|---|
| Tasks no início | 1, sem Auto Scaling | 1, Auto Scaling de 1 a 3 | continuação de B | 2, sem Auto Scaling |
| Carga | 0,5 C constante por 5 min | 0,3 C por 2 min; degrau 1: 0,85 C por 6 min; degrau 2: 1,5 C por 7 min (rampas de 1 min entre eles) | 1 min de rampa até 0,2 C; 0,2 C por 22 min; mais 5 min de observação | 0,8 C constante por 10 min; `stop-task` em 1 task aos 3 min |
| Cenário k6 | `A-baseline` | `BC-escalabilidade` (fases aquecimento, subida-1, degrau-1, subida-2, degrau-2) | `BC-escalabilidade` (fases descida, baixa) | `D-falha` |
| Duração aproximada | 6 min | ~47 min (B e C juntos) | (B e C juntos) | 13 min |

**Por que essas cargas:**

- **A:** 0,5 C deixa a task com folga, perto de 50% de CPU, e serve de referência de latência e vazão sem fila.
- **B (em degraus):**
  - **Degrau 1:** 0,85 C deixa a única task em ~85% de CPU, acima do alvo; o target tracking calcula ⌈1 · 85/60⌉ = 2 tasks, e cada uma fica em ~42%.
  - **Degrau 2:** 1,5 C, com 2 tasks, dá ~75% em cada, o que pede ⌈2 · 75/60⌉ = 3 (o máximo); com 3 tasks, cada uma fica em ~50%, sem oscilar.
  - **Duração:** cada degrau precisa de cerca de 3 minutos acima do alvo para o alarme, mais o início e o health check da task nova; 6 e 7 minutos dão margem.

  **Por que não saltar direto para uma carga maior que C:** com mais carga do que a capacidade das tasks existentes, a fila da API cresce sem limite enquanto o scale-out não termina.
  - O ALB responde 504 depois de 60 s sem resposta, mas a task continua processando os pedidos abandonados.
  - O experimento passaria a medir a fila, e não o Auto Scaling.
  - Por isso, cada degrau fica abaixo da capacidade das tasks que já existem.
- **C:** com 0,2 C e 3 tasks, a CPU fica perto de 7%. O alarme de scale-in do target tracking exige cerca de 15 minutos abaixo do limite inferior; depois disso, ⌈3 · 7/60⌉ = 1 task. Os 22 minutos de carga baixa mais 5 de observação cobrem essa espera.
- **D:** 0,8 C em 2 tasks dá ~40% de CPU em cada. Sem uma delas, a restante recebe 80% de C: trabalha mais, mas ainda sem saturar, o que permite separar o efeito da falha do efeito de sobrecarga.

## 4. Hipóteses e critérios

| | Hipótese | Confirmada se | Refutada ou inconclusiva se |
|---|---|---|---|
| H-A | Uma task atende 0,5 C com vazão igual à oferecida, latência estável e sem erros | Vazão ≥ 95% da oferecida, erros < 1%, CPU média entre 35% e 65% | Fila crescente, erros ou CPU fora da faixa: revisar a calibração |
| H-B | A CPU acima de 60% dispara o alarme e o serviço chega a 3 tasks; sob a mesma carga, a latência cai depois de cada scale-out | Desejadas 1→2→3, cada degrau com uma task saudável no ALB; em cada degrau de carga, p95 com mais tasks menor que com menos (tabela "Mesma carga, número de tasks diferente") | Sem alarme ou sem novas tasks: registrar CPU, estado dos alarmes, atividades do Auto Scaling e possível causa (seção 7) |
| H-C | Com carga baixa, o serviço volta a 1 task depois do alarme de scale-in, sem erros | Desejadas 3→1 (em um ou mais degraus) dentro da observação; erros < 1% | Tasks não reduzidas: registrar o tempo observado e o estado do alarme baixo |
| H-D | O ECS substitui a task encerrada e volta a 2 tasks saudáveis; os erros ficam restritos à parada | Substituta saudável no ALB; erros na janela da falha < 1% das requisições | Sem substituta, ou erros persistentes depois da recuperação |

As faixas numéricas são critérios de leitura definidos antes dos testes; os resultados são registrados como medidos, mesmo quando fora delas.

## 5. Métricas e origem

| Indicador | Fonte | Arquivo da execução |
|---|---|---|
| Vazão (RPS), latência p50/p95/p99, erros, iterações descartadas | k6, por requisição e com a fase | `k6-bruto.csv.gz`, `resumo-k6.json` |
| Distribuição entre tasks | Header `x-instance-id` de cada resposta | `k6-bruto.csv.gz` (métrica `respostas_por_instancia`) |
| Tasks desejadas, em execução e saudáveis; alvos do ALB | ECS `describe-services`/`describe-tasks` e `describe-target-health`, a cada 10 s | `timeline.csv` |
| CPU e memória do serviço | CloudWatch `AWS/ECS`, períodos de 1 min (média e máximo) | `aws/metricas-ecs-*.json` |
| Alvos saudáveis, requisições, 5XX e p95 no ALB | CloudWatch `AWS/ApplicationELB`, 1 min | `aws/metricas-alb-*.json` |
| Gatilho do scaling | Histórico dos alarmes do target tracking | `aws/alarmes-historico.json` |
| Decisões de escala | Atividades do Application Auto Scaling | `aws/autoscaling-atividades.json` |
| Eventos do serviço e das tasks | Eventos do ECS; `describe-tasks` (motivo e horários de parada) | `aws/ecs-eventos.json`, `aws/tasks.json` |
| Configuração | Região, imagem (tag e digest), task definition, política, parâmetros do k6 | `metadata.json` |

## 6. Definição dos tempos

- **Scale-out (por degrau):** do alarme de alta entrar em `ALARM` (o gatilho observado) até a primeira amostra com alvos saudáveis no ALB ≥ novas tasks desejadas (a task disponível). Também são registrados dois intervalos:
  - decisão do Auto Scaling → task disponível;
  - carga oferecida acima do alvo para as tasks existentes (0,6 C antes do 1º degrau, 1,2 C antes do 2º) → task disponível.
- **Mesma carga, número de tasks diferente:** em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. Assim latência e vazão são comparadas sob a mesma carga oferecida.
- **Scale-in:** do início da redução da carga (fase `descida`) até a redução das tasks desejadas. Também é registrado o intervalo alarme de baixa → redução.
- **Recuperação (D):** do pedido de `stop-task` até as tasks saudáveis voltarem ao número anterior. Também são registrados o momento em que a substituta aparece e os erros entre 5 s antes da parada e 30 s depois da recuperação.

**Resolução:**

- O estado do serviço é amostrado a cada 10 s, então os tempos têm incerteza dessa ordem.
- As métricas do CloudWatch têm períodos de 1 min.
- Os horários do k6 e da coleta vêm da máquina que roda os testes, e os eventos da AWS vêm do relógio da AWS. Mantenha o relógio local sincronizado (NTP).

## 7. Se o scaling não acontecer

O plano pede registrar configuração, hipótese e possível causa. Antes de repetir, verifique e anote:

1. **CPU:** a CPU média ficou acima do alvo por pelo menos 3 períodos de 1 min (`grafico-cpu-memoria.png`)? Se não, a carga ficou abaixo do esperado: revise C, as iterações descartadas e a capacidade do gerador.
2. **Alarme:** o alarme de alta foi para `ALARM` (`alarmes-historico.json`)? `INSUFFICIENT_DATA` indica falta de métricas do serviço.
3. **Auto Scaling:** há atividades com status de falha (`autoscaling-atividades.json`)? Podem indicar falta de permissão ou de capacidade.
4. **Tasks:** as tasks novas ficaram `PENDING` ou falharam no health check (`ecs-eventos.json`, `tasks.json`)?
5. **Distribuição:** o ALB distribuiu a carga entre as tasks (`grafico-instancias.png`)?

## 8. Repetições, ordem e custo

- **Repetições:** 3 de cada experimento, se o orçamento e o prazo permitirem. Ordem: calibração → A ×3 → B/C ×3 → D ×3.
- **Entre repetições de B/C:** espere o serviço voltar a 1 task. O script recusa iniciar fora da condição inicial.
- **Tempo total de AWS:** cerca de 3 h, com o ALB ativo todo o tempo e de 1 a 3 tasks.

| Experimento | Uso por repetição |
|---|---|
| A | 1 task por ~6 min |
| B/C | ~47 min, com até 3 tasks |
| D | 2 a 3 tasks por ~13 min |

Estime o custo na região escolhida (horas de task, ALB e IPs públicos) e registre a aprovação do grupo antes de começar, como manda o plano. Este documento não presume preços.

## 9. Ameaças à validade

- **Gerador de carga:** o k6 roda fora da AWS, então a latência inclui a internet. Registre de onde o teste partiu e mantenha o mesmo local entre repetições. Iterações descartadas (`dropped_iterations`) indicam que o gerador não sustentou a carga planejada.
- **Variação do Fargate:** a CPU de 0,25 vCPU pode variar entre tasks e horários. Por isso a calibração acontece no mesmo dia dos experimentos.
- **Amostragem:** o estado a cada 10 s e as métricas de 1 min limitam a precisão dos tempos (seção 6).
- **Health checks:** os valores ajustados (10 s, 2 acertos, drenagem de 30 s) fazem parte da configuração e influenciam os tempos medidos; mudar esses valores exige refazer os experimentos.
- **Interpretação:** mais tasks não provam melhor desempenho por si só. As conclusões relacionam o número de tasks com vazão, latência e erros na mesma carga oferecida (tabela "Mesma carga, número de tasks diferente" do resumo).
- **Fila sem limite na API:** sob carga maior que a capacidade, os pedidos esperam indefinidamente, e os que passam de 60 s recebem 504 do ALB, mas continuam sendo processados. O desenho em degraus evita essa situação. Se ela aparecer (latência crescente e 504), registre como limitação; descartar pedidos excedentes na API seria uma melhoria futura.

## 10. Validação local

O ambiente de `tests/local` (3 réplicas com 0,25 vCPU e 512 MiB atrás de um nginx) valida o script k6, o orquestrador e a análise sem AWS. Ele **não** tem Auto Scaling nem ECS:

- em B/C as 3 réplicas ficam fixas;
- em D a réplica é parada e religada pelo próprio script.

Os resultados locais servem para conferir a ferramenta, não como evidência dos experimentos. Exemplos em [`results/exemplo-local/`](results/exemplo-local/).
