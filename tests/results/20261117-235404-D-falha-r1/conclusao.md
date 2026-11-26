# Conclusão — D-falha (repetição 1)

Revisado pela Pessoa 3 em 25/11/2026 com `resumo.md`, `timeline.csv`, `eventos.json`, `aws/tasks.json`, `aws/ecs-eventos.json` e as respostas por instância em `k6-bruto.csv.gz`. Horários em UTC, relativos ao `stop-task` (23:57:10.8).

## Hipótese

O ECS inicia uma task substituta e volta a 2 tasks saudáveis; a task restante absorve a carga e os erros ficam restritos ao momento da parada.

## Observação real

- **Confirmada, sem erros.** Houve 0 erros nas 119 requisições da janela da falha e nas 720 da execução. O ALB não registrou respostas 5XX (`aws/metricas-alb-HTTPCode_*`).

| Instante | O que aconteceu | Fonte |
|---|---|---|
| +0 s | Pedido de `stop-task` para a task `09a50126…` (us-east-2b) | `eventos.json` |
| +2 s | O ECS marca a task como parando (`stoppingAt`), mas ela continua registrada e saudável no ALB | `aws/tasks.json`, `timeline.csv` |
| +35,7 s | Última resposta da task parada recebida pelo k6 | `k6-bruto.csv.gz` |
| +36,5 s | O ECS tira o alvo do ALB e inicia a drenagem | `eventos.json` |
| +37 s | A substituta `c6767d66…` é criada; a coleta registra a queda para 1 alvo saudável | `aws/tasks.json`, `timeline.csv` |
| +68 s | A substituta fica saudável no ALB: **recuperação em 68 s** | `timeline.csv` |
| +71 s | Primeira resposta da substituta | `k6-bruto.csv.gz` |
| +97 s | O container da task parada encerra, com código 0, depois da drenagem de 30 s | `aws/tasks.json` |

- **O cliente não viu a falha.** O `stop-task` é uma parada ordenada: o ECS tira o alvo do ALB e drena as conexões antes de encerrar o container. A task restante também tinha folga, com cerca de 0,77 C de carga efetiva para uma task de capacidade C.
- **A capacidade ficou reduzida por cerca de 31 s, não por 68.** Nos primeiros 37 s, a task parada ainda atendia, enquanto o ECS reagia ao pedido. Só uma task atendeu de +37 s a +68 s. Nesse intervalo, as 36 requisições tiveram p50 de 707 ms e p95 de 1710 ms, contra p50 de 689 ms e p95 de 1082 ms com 2 tasks ("Mesma carga" em `resumo.md`). A latência subiu, mas não houve fila crescente nem timeout.
- **"Substituta em 37 s"** mede o tempo até o ECS agir, e coincide com a saída da task parada do ALB. Da criação da substituta até ela ficar saudável passaram 31 s, na mesma ordem dos 30–35 s do scale-out de B.

## Limitações

- Uma repetição.
- A falha foi controlada (`stop-task`, com drenagem). Uma queda abrupta, com o processo morto sem drenagem, só seria detectada pelo health check do ALB (2 falhas a cada 10 s, em `infrastructure/scripts/Provision.ps1`) e pode gerar erros nesse intervalo. Esse caso não foi testado.
- O estado foi amostrado a cada 10 s, e o k6 rodou 4,2% mais devagar que o relógio (carga efetiva de 96%).

## Próximos ajustes

- Se houver repetições, manter o `stop-task`. Uma variante com falha abrupta fica como trabalho futuro, fora do plano atual.
