# Tabela experimental

Gerada por `tests/analysis/analisar.py consolidar`. Média ± desvio-padrão (n = execuções com o indicador).

| Experimento | Ambiente | Execuções | vazao_rps | p95_ms | erros_pct | cpu_media_pct | tasks_max | scale_out_1o_degrau_s | scale_in_s | scale_out_2o_degrau_s | recuperacao_s | erros_falha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-baseline | local | 1 | 0.85 ± — (n=1) | 330.6 ± — (n=1) | 0 ± — (n=1) | — | — | — | — | — | — | — |
| BC-escalabilidade | local | 1 | 1.02 ± — (n=1) | 398.7 ± — (n=1) | 0 ± — (n=1) | — | 3 ± — (n=1) | — | — | — | — | — |
| D-falha | local | 1 | 1.38 ± — (n=1) | 479.2 ± — (n=1) | 0.8 ± — (n=1) | — | — | — | — | — | 35 ± — (n=1) | 2 ± — (n=1) |
| calibracao | local | 1 | 1.74 ± — (n=1) | 3890.6 ± — (n=1) | 0 ± — (n=1) | — | — | — | — | — | — | — |
| smoke | local | 1 | 2.26 ± — (n=1) | 500 ± — (n=1) | 0 ± — (n=1) | — | — | — | — | — | — | — |

## Mesma carga, número de tasks diferente

Requisições de cada fase de carga constante separadas pelo número de tasks saudáveis no momento (média entre execuções).

| Experimento | Ambiente | Fase | Oferecida (req/s) | Tasks saudáveis | Execuções | Vazão (req/s) | p95 (ms) | Erros (%) |
|---|---|---|---|---|---|---|---|---|
| A-baseline | local | constante | 0.867 | 1 | 1 | 0.86 ± — (n=1) | 330.6 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | local | aquecimento | 0.517 | 3 | 1 | 0.5 ± — (n=1) | 335 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | local | baixa | 0.35 | 3 | 1 | 0.35 ± — (n=1) | 316.6 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | local | degrau-1 | 1.483 | 3 | 1 | 1.47 ± — (n=1) | 392.5 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | local | degrau-2 | 2.617 | 3 | 1 | 2.62 ± — (n=1) | 405.5 ± — (n=1) | 0 ± — (n=1) |
| D-falha | local | constante | 1.4 | 1 | 1 | 1.4 ± — (n=1) | 479.2 ± — (n=1) | 0 ± — (n=1) |
| D-falha | local | constante | 1.4 | 2 | 1 | 1.38 ± — (n=1) | 451.5 ± — (n=1) | 0.96 ± — (n=1) |

## Execuções

| Pasta | Experimento | Rep. | vazao_rps | p95_ms | erros_pct | cpu_media_pct | tasks_max | scale_out_1o_degrau_s | scale_in_s | scale_out_2o_degrau_s | recuperacao_s | erros_falha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261113-014830-smoke-r1-local | smoke | 1 | 2.262 | 500 | 0 | — | — | — | — | — | — | — |
| 20261113-014909-calibracao-r1-local | calibracao | 1 | 1.738 | 3890.6 | 0 | — | — | — | — | — | — | — |
| 20261113-021556-A-baseline-r1-local | A-baseline | 1 | 0.855 | 330.6 | 0 | — | — | — | — | — | — | — |
| 20261113-021744-BC-escalabilidade-r1-local | BC-escalabilidade | 1 | 1.018 | 398.7 | 0 | — | 3 | — | — | — | — | — |
| 20261113-022236-D-falha-r1-local | D-falha | 1 | 1.383 | 479.2 | 0.797 | — | — | — | — | — | 35 | 2 |
