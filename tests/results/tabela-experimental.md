# Tabela experimental

Gerada por `tests/analysis/analisar.py consolidar`. Média ± desvio-padrão (n = execuções com o indicador).

| Experimento | Ambiente | Execuções | vazao_rps | p95_ms | erros_pct | cpu_media_pct | tasks_max | carga_ate_pronta_1o_degrau_s | scale_out_1o_degrau_s | scale_out_2o_degrau_s | scale_in_s | recuperacao_s | erros_falha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-baseline | aws | 1 | 0.72 ± — (n=1) | 1014.4 ± — (n=1) | 0 ± — (n=1) | 48.7 ± — (n=1) | — | — | — | — | — | — | — |
| BC-escalabilidade | aws | 1 | 0.84 ± — (n=1) | 1300.6 ± — (n=1) | 0 ± — (n=1) | 32.4 ± — (n=1) | 3 ± — (n=1) | 433 ± — (n=1) | 35 ± — (n=1) | 30 ± — (n=1) | 1108 ± — (n=1) | — | — |
| D-falha | aws | 1 | 1.15 ± — (n=1) | 1106.3 ± — (n=1) | 0 ± — (n=1) | 39.8 ± — (n=1) | — | — | — | — | — | 68 ± — (n=1) | 0 ± — (n=1) |
| calibracao | aws | 1 | 1.49 ± — (n=1) | 3829.2 ± — (n=1) | 0 ± — (n=1) | 100 ± — (n=1) | — | — | — | — | — | — | — |
| smoke | aws | 1 | 0.93 ± — (n=1) | 738.4 ± — (n=1) | 0 ± — (n=1) | — | — | — | — | — | — | — | — |

Indicadores:

- `vazao_rps`: requisições /work bem-sucedidas por segundo na janela do k6.
- `p95_ms`: percentil 95 da latência do /work (posto mais próximo; o resumo do k6 interpola e pode diferir em alguns ms).
- `erros_pct`: requisições /work com falha (status inesperado ou timeout).
- `cpu_media_pct`: CPU média do serviço nos minutos inteiros da janela do k6 (CloudWatch, 1 min).
- `tasks_max`: maior número de tasks desejadas.
- `carga_ate_pronta_1o_degrau_s`: da carga oferecida passar da CPU-alvo com 1 task até a 2ª task saudável no ALB (reação completa: métrica, alarme e ECS).
- `scale_out_1o_degrau_s`: da decisão do Auto Scaling (1→2) até a nova task saudável no ALB.
- `scale_out_2o_degrau_s`: da decisão do Auto Scaling (2→3) até a nova task saudável no ALB; não conta desde o 1º alarme, que fica em ALARM entre os degraus.
- `scale_in_s`: do início da redução da carga até a primeira decisão de scale-in.
- `recuperacao_s`: D: do pedido de parada até o ALB voltar ao número de alvos saudáveis anterior.
- `erros_falha`: D: erros do k6 na janela da falha.

## Mesma carga, número de tasks diferente

Requisições de cada fase de carga constante separadas pelo número de tasks saudáveis no momento (média entre execuções). `> 1 s` é a fração de requisições acima de 1 s: perto de 5%, o p95 muda de patamar por poucas requisições, e o p50 é a comparação mais estável.

| Experimento | Ambiente | Fase | Planejada (req/s) | Tasks saudáveis | Execuções | Requisições | Vazão (req/s) | p50 (ms) | p95 (ms) | > 1 s (%) | Erros (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-baseline | aws | constante | 0.75 | 1 | 1 | 225 | 0.72 ± — (n=1) | 660.1 ± — (n=1) | 1014.4 ± — (n=1) | 5.8 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | aquecimento | 0.45 | 1 | 1 | 51 | 0.42 ± — (n=1) | 691.5 ± — (n=1) | 809.8 ± — (n=1) | 2 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | baixa | 0.3 | 1 | 1 | 24 | 0.3 ± — (n=1) | 673.9 ± — (n=1) | 724.1 ± — (n=1) | 4.2 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | baixa | 0.3 | 2 | 1 | 68 | 0.29 ± — (n=1) | 684.2 ± — (n=1) | 750.7 ± — (n=1) | 1.5 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | baixa | 0.3 | 3 | 1 | 345 | 0.31 ± — (n=1) | 689.8 ± — (n=1) | 1163.3 ± — (n=1) | 6.4 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | degrau-1 | 1.283 | 1 | 1 | 442 | 1.23 ± — (n=1) | 700.2 ± — (n=1) | 1476 ± — (n=1) | 13.1 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | degrau-2 | 2.25 | 2 | 1 | 353 | 2.12 ± — (n=1) | 727.7 ± — (n=1) | 1391.8 ± — (n=1) | 9.6 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | degrau-2 | 2.25 | 3 | 1 | 550 | 2.17 ± — (n=1) | 678.7 ± — (n=1) | 1074.2 ± — (n=1) | 6 ± — (n=1) | 0 ± — (n=1) |
| D-falha | aws | constante | 1.2 | 1 | 1 | 36 | 1.15 ± — (n=1) | 706.7 ± — (n=1) | 1709.8 ± — (n=1) | 13.9 ± — (n=1) | 0 ± — (n=1) |
| D-falha | aws | constante | 1.2 | 2 | 1 | 684 | 1.15 ± — (n=1) | 689.2 ± — (n=1) | 1082.4 ± — (n=1) | 5.4 ± — (n=1) | 0 ± — (n=1) |

## Execuções

| Pasta | Experimento | Rep. | vazao_rps | p95_ms | erros_pct | cpu_media_pct | tasks_max | carga_ate_pronta_1o_degrau_s | scale_out_1o_degrau_s | scale_out_2o_degrau_s | scale_in_s | recuperacao_s | erros_falha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261117-222155-smoke-r1 | smoke | 1 | 0.934 | 738.4 | 0 | — | — | — | — | — | — | — | — |
| 20261117-223019-calibracao-r1 | calibracao | 1 | 1.491 | 3829.2 | 0 | 100 | — | — | — | — | — | — | — |
| 20261117-225146-A-baseline-r1 | A-baseline | 1 | 0.718 | 1014.4 | 0 | 48.7 | — | — | — | — | — | — | — |
| 20261117-230132-BC-escalabilidade-r1 | BC-escalabilidade | 1 | 0.837 | 1300.6 | 0 | 32.4 | 3 | 433 | 35 | 30 | 1108 | — | — |
| 20261117-235404-D-falha-r1 | D-falha | 1 | 1.152 | 1106.3 | 0 | 39.8 | — | — | — | — | — | 68 | 0 |
