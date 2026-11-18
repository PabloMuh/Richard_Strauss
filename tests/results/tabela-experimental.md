# Tabela experimental

Gerada por `tests/analysis/analisar.py consolidar`. Média ± desvio-padrão (n = execuções com o indicador).

| Experimento | Ambiente | Execuções | vazao_rps | p95_ms | erros_pct | cpu_media_pct | tasks_max | scale_out_1o_degrau_s | scale_in_s | scale_out_2o_degrau_s | recuperacao_s | erros_falha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-baseline | aws | 1 | 0.72 ± — (n=1) | 1014.4 ± — (n=1) | 0 ± — (n=1) | 37.7 ± — (n=1) | — | — | — | — | — | — |
| BC-escalabilidade | aws | 1 | 0.84 ± — (n=1) | 1300.6 ± — (n=1) | 0 ± — (n=1) | 31.3 ± — (n=1) | 3 ± — (n=1) | 35 ± — (n=1) | 1150 ± — (n=1) | 210 ± — (n=1) | — | — |
| D-falha | aws | 1 | 1.15 ± — (n=1) | 1106.3 ± — (n=1) | 0 ± — (n=1) | 37.7 ± — (n=1) | — | — | — | — | 68 ± — (n=1) | 0 ± — (n=1) |
| calibracao | aws | 1 | 1.49 ± — (n=1) | 3829.2 ± — (n=1) | 0 ± — (n=1) | 71.5 ± — (n=1) | — | — | — | — | — | — |
| smoke | aws | 1 | 0.93 ± — (n=1) | 738.4 ± — (n=1) | 0 ± — (n=1) | — | — | — | — | — | — | — |

## Mesma carga, número de tasks diferente

Requisições de cada fase de carga constante separadas pelo número de tasks saudáveis no momento (média entre execuções).

| Experimento | Ambiente | Fase | Oferecida (req/s) | Tasks saudáveis | Execuções | Vazão (req/s) | p95 (ms) | Erros (%) |
|---|---|---|---|---|---|---|---|---|
| A-baseline | aws | constante | 0.75 | 1 | 1 | 0.72 ± — (n=1) | 1038.2 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | aquecimento | 0.45 | 1 | 1 | 0.42 ± — (n=1) | 809.8 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | baixa | 0.3 | 2 | 1 | 0.29 ± — (n=1) | 750.7 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | baixa | 0.3 | 3 | 1 | 0.31 ± — (n=1) | 1163.3 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | degrau-1 | 1.283 | 1 | 1 | 1.23 ± — (n=1) | 1476 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | degrau-2 | 2.25 | 2 | 1 | 2.12 ± — (n=1) | 1391.8 ± — (n=1) | 0 ± — (n=1) |
| BC-escalabilidade | aws | degrau-2 | 2.25 | 3 | 1 | 2.17 ± — (n=1) | 1074.2 ± — (n=1) | 0 ± — (n=1) |
| D-falha | aws | constante | 1.2 | 1 | 1 | 1.15 ± — (n=1) | 1709.8 ± — (n=1) | 0 ± — (n=1) |
| D-falha | aws | constante | 1.2 | 2 | 1 | 1.15 ± — (n=1) | 1084.3 ± — (n=1) | 0 ± — (n=1) |

## Execuções

| Pasta | Experimento | Rep. | vazao_rps | p95_ms | erros_pct | cpu_media_pct | tasks_max | scale_out_1o_degrau_s | scale_in_s | scale_out_2o_degrau_s | recuperacao_s | erros_falha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261117-222155-smoke-r1 | smoke | 1 | 0.934 | 738.4 | 0 | — | — | — | — | — | — | — |
| 20261117-223019-calibracao-r1 | calibracao | 1 | 1.491 | 3829.2 | 0 | 71.5 | — | — | — | — | — | — |
| 20261117-225146-A-baseline-r1 | A-baseline | 1 | 0.718 | 1014.4 | 0 | 37.7 | — | — | — | — | — | — |
| 20261117-230132-BC-escalabilidade-r1 | BC-escalabilidade | 1 | 0.837 | 1300.6 | 0 | 31.3 | 3 | 35 | 1150 | 210 | — | — |
| 20261117-235404-D-falha-r1 | D-falha | 1 | 1.152 | 1106.3 | 0 | 37.7 | — | — | — | — | 68 | 0 |
