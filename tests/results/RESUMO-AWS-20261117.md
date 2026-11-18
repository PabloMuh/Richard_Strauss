# Experimentos na AWS — 17/11/2026 (1 repetição de cada)

> ⚠️ **Feito pelo Claude (claudinho) — pendente de revisão da equipe.** Gerado automaticamente em 17/11/2026 a partir das execuções na AWS conduzidas com a Pessoa 1. Conferir números, interpretação e conclusões antes de usar no relatório.

## Ambiente

- Região `us-east-2` (única liberada pela SCP da conta); ECS Fargate, tasks de 0,25 vCPU / 512 MiB, ALB, VPC padrão. Detalhes da implantação: [docs/deploy-aws-20261117.md](../../docs/deploy-aws-20261117.md).
- Imagem dos experimentos A, B/C e D: `richard-strauss:api-62f1e8e` (com a correção de keep-alive). Smoke e calibração rodaram com `api-189bf27` (antes da correção, que não altera o custo de CPU de `/work`).
- k6 1.0.0 via Docker, executado de uma máquina local (WSL2) pela internet até o ALB.
- Auto Scaling: target tracking `ECSServiceAverageCPUUtilization`, alvo 60%, 1–3 tasks, cooldown 60 s (out) / 180 s (in).

## Resultados

| Experimento | Pasta | Requisições | Erros | p95 | Principal resultado |
|---|---|---|---|---|---|
| Smoke | `20261117-222155-smoke-r1` | 9 | 0% | 706 ms | Todos os checks aprovados com 2 tasks |
| Calibração | `20261117-223019-calibracao-r1` | 283 | 0% | 3.829 ms (fila cheia) | **C = 1,50 req/s por task** (vazão estável) |
| A · Baseline | `20261117-225146-A-baseline-r1` | 225 | 0% | 1.014 ms | 1 task a 0,5 C: CPU média 38%, máx. 58% |
| B · Scale-out | `20261117-230132-BC-escalabilidade-r1` | 2.091 (B+C) | 0% | 1.301 ms | 1→2 tasks: task pronta 35 s após o alarme; 2→3: 210 s após o alarme. No degrau de 1,5 C, p95 1.392 ms com 2 tasks e 1.074 ms com 3 |
| C · Scale-in | (mesma execução) | — | 0% | — | 3→2 em 1.150 s e 2→1 em 1.397 s após a redução da carga (alarme de baixa exige ~15 min abaixo do alvo) |
| D · Falha | `20261117-235404-D-falha-r1` | 720 | 0% | 1.106 ms | Substituta em 37 s; 2 tasks saudáveis de novo em 68 s; 0 erros em 119 requisições na janela da falha (p95 1,3 s → 1,7 s → 1,1 s) |

Tabela gerada pela análise: [tabela-experimental.md](tabela-experimental.md). Cada pasta tem `resumo.md`, gráficos, `timeline.csv`, eventos e métricas do CloudWatch (`aws/`).

## Erro de aplicação encontrado e corrigido

A primeira execução do baseline (`pre-correcao/20261117-223742-A-baseline-r1`, imagem `api-189bf27`) teve **1 erro em 225 (0,44%)**: um HTTP 502 gerado pelo ALB em 156 ms, sem registro da requisição nos logs da API. Causa: o Uvicorn fechava conexões ociosas após 5 s (padrão), e o ALB reutiliza conexões por até 60 s. Correção na aplicação (commit `62f1e8e`, branch `pessoa1/deploy-aws`): `KEEP_ALIVE_TIMEOUT` = 75 s. Repetido o baseline com a nova imagem: 0 erros. A execução antiga fica fora da tabela consolidada.

## Observações preliminares (a revisar)

1. **O tempo de reação do scale-out é dominado pelo alarme.** Do momento em que a carga passou do alvo até a 2ª task ficar pronta foram ~438 s, dos quais só 35 s entre a decisão e a task saudável. O alarme de alta do target tracking exige 3 minutos consecutivos acima de 60%, somados ao atraso de publicação das métricas do CloudWatch.
2. **Mais tasks reduziram a latência sob a mesma carga** (degrau de 1,5 C: p95 de 1.392 ms com 2 tasks para 1.074 ms com 3), sem mudar a vazão, que já acompanhava a carga oferecida. Como o plano adverte, mais tasks não provam melhora sozinhas; aqui a melhora aparece na latência.
3. **O scale-in é lento por desenho** (~19–23 min): o alarme de baixa exige ~15 min abaixo do alvo, e a redução acontece em degraus, com cooldown de 180 s.
4. **Tolerância a falhas:** o ECS recolocou a task em ~1 min sem erros visíveis ao cliente. A drenagem de 30 s no target group e a task restante com folga (0,8 C) explicam a ausência de erros.

## Limitações

- **1 repetição por cenário** (o plano prefere 3); não há média nem desvio-padrão.
- Gerador de carga numa única máquina doméstica; a latência inclui a rede até `us-east-2`.
- Tempos de transição medidos por amostragem a cada 10 s.
- Smoke e calibração com a imagem anterior à correção de keep-alive.

## Próximos passos sugeridos

- Pessoa 3: revisar a análise, preencher os `conclusao.md` e decidir se roda repetições 2 e 3.
- Pessoa 4: usar os gráficos `grafico-tasks.png` (B/C) e `grafico-carga-latencia.png` (D) no relatório, citando as pastas de origem.
- Pessoa 2: registrar o custo real da sessão no Billing.
