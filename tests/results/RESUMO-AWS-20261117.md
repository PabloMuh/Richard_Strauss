# Experimentos na AWS — 17/11/2026 (uma repetição de cada)

Resumo revisado pela Pessoa 3 em 25/11/2026. A primeira versão, de 17/11, foi gerada com ferramenta de IA durante a execução com a Pessoa 1 (commit `629f0a7`). A revisão conferiu cada número com os arquivos brutos e corrigiu a análise. O que mudou está em [Revisão de 25/11](#revisão-de-2511). As interpretações por experimento estão nos `conclusao.md` de cada pasta.

## Ambiente

- Região `us-east-2`, a única liberada pela SCP da conta. ECS Fargate com tasks de 0,25 vCPU e 512 MiB, ALB e VPC padrão. Implantação: [docs/deploy-aws-20261117.md](../../docs/deploy-aws-20261117.md).
- A, B/C e D usaram a imagem `richard-strauss:api-62f1e8e`, com a correção do keep-alive. O smoke e a calibração usaram `api-189bf27`; a correção não altera o custo de CPU de `/work`.
- O k6 1.0.0 rodou em Docker numa máquina local (WSL2) e chegou ao ALB pela internet.
- Auto Scaling: target tracking de `ECSServiceAverageCPUUtilization` com alvo de 60%, de 1 a 3 tasks e cooldowns de 60 s (aumento) e 180 s (redução).
- Capacidade de uma task: **C = 1,50 req/s** (calibração).

## Resultados

| Experimento | Pasta | Requisições | Erros | p50 / p95 | Principal resultado |
|---|---|---|---|---|---|
| Smoke | `20261117-222155-smoke-r1` | 9 (3 por rota) | 0% | 657 / 738 ms (`/work`) | Todos os checks aprovados com 2 tasks |
| Calibração | `20261117-223019-calibracao-r1` | 283 | 0% | 2487 / 3829 ms (fila cheia) | **C = 1,50 req/s por task** (vazão estável de 1,501 req/s, CPU a 100%) |
| A · Baseline | `20261117-225146-A-baseline-r1` | 225 | 0% | 660 / 1014 ms | 1 task a cerca de 0,48 C: CPU de 48,7% nos minutos inteiros |
| B · Scale-out | `20261117-230132-BC-escalabilidade-r1` | 2091 (B+C) | 0% | 692 / 1301 ms | 1→2 e 2→3: **35 s e 30 s** da decisão do Auto Scaling até a task saudável no ALB; 433 s da carga acima do alvo até a 2ª task |
| C · Scale-in | (mesma execução) | — | 0% | — | 3→2 e 2→1 em **1108 s e 1348 s** após a redução da carga; uma task por vez |
| D · Falha | `20261117-235404-D-falha-r1` | 720 | 0% | 690 / 1106 ms | Recuperação (2 alvos saudáveis) em **68 s**; capacidade reduzida por cerca de 31 s; 0 erros nas 119 requisições da janela da falha |

A tabela consolidada, com a legenda de cada indicador, está em [tabela-experimental.md](tabela-experimental.md). Cada pasta tem `resumo.md`, `conclusao.md`, gráficos, `timeline.csv`, eventos e métricas do CloudWatch (`aws/`).

## Interpretação

1. **Scale-out: o ECS é rápido, as métricas não.** Da decisão do Auto Scaling até a nova task saudável no ALB passaram 35 s (1→2) e 30 s (2→3). No primeiro degrau, a reação completa levou 433 s. O alarme de alta precisa de 3 datapoints de 1 min acima de 60% e só mudou de estado quase 3 min depois do terceiro. O segundo degrau não precisou de nova transição: o alarme continuou em ALARM e a política pediu a 3ª task logo após o cooldown de 60 s (171 s de ponta a ponta).
2. **Scale-in: lento por desenho.** O alarme de baixa precisa de 15 datapoints abaixo de 54% e começou a contar ainda no degrau de carga alta: com 3 tasks, a CPU já estava abaixo de 54%. Depois do alarme, a política retirou uma task de cada vez: a primeira 6 min depois (motivo não registrado nas atividades exportadas) e a segunda após o cooldown de 180 s. A volta a 1 task levou cerca de 22 min após a redução da carga.
3. **Mesma carga, número de tasks diferente.**
   - Com carga alta (1,5 C), passar de 2 para 3 tasks reduziu o p50 de 728 para 679 ms e o p95 de 1392 para 1074 ms, com a mesma vazão e sem erros.
   - Com carga baixa (0,2 C), o p50 ficou igual com 1, 2 ou 3 tasks (674 a 690 ms). Mais tasks só melhoram a latência quando cada task está carregada.
   - O p95 maior com 3 tasks que com 2 na carga baixa vem da cauda periódica explicada no item 5, não do número de tasks.
4. **Falha: recuperação sem erro visível ao cliente.**
   - Depois do `stop-task`, a task parada ainda atendeu por cerca de 36 s, até o ECS tirá-la do ALB e criar a substituta. A substituta ficou saudável 31 s depois, 68 s após o pedido de parada.
   - Não houve erro porque a parada é ordenada (drenagem de 30 s antes de encerrar o container) e a task restante tinha folga (cerca de 0,77 C).
   - Durante os 31 s com uma task, o p95 subiu de cerca de 1,1 s para 1,7 s.
5. **Cauda de latência periódica.**
   - Em todas as tasks, de 4% a 10% das requisições passaram de 1 s, e a maioria delas (de 49% a 80%) começa sempre na mesma faixa de 5 s de um ciclo de 30 s, contra cerca de 17% esperados ao acaso. Na calibração, em que a lentidão vem da fila, a concentração cai para 19%.
   - O ciclo coincide com o intervalo do health check do container, que inicia um interpretador Python na task de 0,25 vCPU. É a causa provável, mas não foi testada isoladamente.
   - Por isso, com carga baixa, o p95 depende de poucas requisições, e o p50 é a comparação mais estável.

## Erro de aplicação encontrado e corrigido

- A primeira execução do baseline (`pre-correcao/20261117-223742-A-baseline-r1`, imagem `api-189bf27`) teve **1 erro em 225 (0,44%)**: um HTTP 502 gerado pelo ALB em 156 ms (`HTTPCode_ELB_5XX_Count` = 1, `HTTPCode_Target_5XX_Count` = 0).
- **Causa provável:** o Uvicorn fechava conexões ociosas após 5 s, menos que os 60 s de idle timeout do ALB.
- **Correção:** a Pessoa 1 passou o valor para 75 s (`KEEP_ALIVE_TIMEOUT`, commit `62f1e8e`).
- **Verificação:** com a imagem corrigida, A, B/C e D somaram 3036 requisições sem erro. A execução antiga fica fora da tabela consolidada.

## Revisão de 25/11

Conferido contra os dados brutos:

- **Contagens e erros.** Requisições e falhas de cada `resumo.md` batem com o resumo do próprio k6 (`resumo-k6.json`) e com o `RequestCount` do ALB. A, B/C e D não têm 5XX do ALB nem do alvo.
- **CPU e eventos.** As médias de CPU foram recalculadas a partir de `aws/metricas-ecs-CPUUtilization.json`. Os horários de alarmes, decisões e registro de alvos foram conferidos com `aws/alarmes-historico.json`, `aws/autoscaling-atividades.json` e `eventos.json`.
- **Alinhamento de relógios.** Os timestamps do CSV do k6 batem com os eventos do ECS com diferença de até ~2 s, até o fim da execução mais longa. As respostas de cada task começam e terminam junto com o registro e a retirada dela no ALB.
- **Reprodutibilidade.** Rodando o `analisar.py` de 17/11, os resumos de 17/11 saem idênticos aos versionados. Nenhum número foi editado à mão.

Correções na análise (`tests/analysis/analisar.py`, com testes) e resumos regenerados:

- **2º degrau do scale-out.** Cada degrau passa a ser medido a partir da própria decisão do Auto Scaling. Antes, o 2→3 reaproveitava o primeiro alarme e a primeira decisão e mostrava 210 s; o valor correto é 30 s.
- **Decisões de scale-in.** O 3→2 aparecia sem decisão, e o 2→1 com a decisão do 3→2. Agora cada redução usa a sua atividade, aceitando a diferença de até um ciclo de coleta entre a amostra e a decisão.
- **CPU média.** Passa a considerar só os minutos inteiros dentro da janela. O A mostrava 37,7% porque incluía minutos parciais; o valor correto é 48,7%.
- **Ritmo do k6.** O gerador cumpriu todas as iterações do plano, mas 4,0% a 4,3% mais devagar que o relógio (provavelmente o relógio do container no WSL2). A análise mede esse fator, corrige os instantes derivados do plano ("carga acima do alvo" e "redução da carga") e estende a última fase até o fim real do k6. Com isso, 438 s passaram a 433 s, 194 s a 171 s e 1150 s a 1108 s.
- **Novos indicadores.** Fração de requisições acima de 1 s, CPU por fase, cauda de latência por task e, em D, o tempo até a queda no ALB.

## Limitações

- **Uma repetição por cenário.** O plano prefere três. Não há média nem desvio-padrão, e os tempos descrevem esta sessão.
- **Gerador numa máquina doméstica.** A latência inclui a rede até `us-east-2`. O k6 cumpriu o plano cerca de 4% mais devagar que o relógio, e a carga efetiva foi cerca de 96% da planejada.
- **Resolução das medições.** O estado do serviço foi amostrado a cada 10 s, e o horário de cada amostra é o início da coleta, com o estado lido nos segundos seguintes. As métricas do CloudWatch estão em períodos de 1 min.
- **Imagem.** Smoke e calibração usaram a imagem anterior à correção do keep-alive.
- **Falha controlada.** D testou um `stop-task` com drenagem; uma queda abrupta não foi testada.

## Próximos passos

- **Pessoa 4:** usar no relatório os gráficos `grafico-tasks.png` de B/C e `grafico-carga-latencia.png` de D, além desta interpretação e da [tabela](tabela-experimental.md), citando as pastas de origem. Os tempos de scale-out devem ser citados por degrau (35 s e 30 s), nunca os 210 s da versão anterior.
- **Equipe:** decidir sobre as repetições 2 e 3. Se não houver nova sessão, declarar a repetição única como limitação.
