# Resumo — BC-escalabilidade (repetição 1)

Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.

## Identificação e configuração

| Campo | Valor |
|---|---|
| Objetivo | B: scale-out com carga em degraus (85% e 150% da capacidade de uma task); C: scale-in após reduzir a carga para 20% |
| Responsável | leonardo-lbp |
| Ambiente | local |
| Região | — |
| Imagem | — |
| Task definition | — |
| Início / fim (UTC) | 2026-11-13T02:17:45.075Z / 2026-11-13T02:21:42.781Z |
| Capacidade de 1 task usada (req/s) | 1.749 |
| Iterações por /work | padrão do servidor |
| Escala de tempo | 0.1 |
| Auto Scaling | desativado |
| Coleta do estado (s) | 5 |

## Resultado geral (k6)

| Requisições | Erros (%) | Vazão (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Iterações descartadas |
|---|---|---|---|---|---|---|
| 242 | 0 | 1.018 | 285.8 | 398.7 | 560.8 | 0 |

## Por fase

| Fase | Duração (s) | Oferecida (req/s) | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) | Respostas por instância |
|---|---|---|---|---|---|---|---|
| aquecimento | 12 | 0.517 | 0.5 | 0 | 316.3 | 335 | local-1: 2, local-2: 2, local-3: 2 |
| subida-1 | 6 | 1 | 1 | 0 | 273.9 | 496.1 | local-1: 2, local-2: 2, local-3: 2 |
| degrau-1 | 36 | 1.483 | 1.472 | 0 | 281.1 | 392.5 | local-1: 18, local-2: 18, local-3: 17 |
| subida-2 | 6 | 2.05 | 2 | 0 | 287.3 | 398.7 | local-1: 4, local-2: 4, local-3: 4 |
| degrau-2 | 42 | 2.617 | 2.619 | 0 | 297.9 | 405.5 | local-1: 37, local-2: 36, local-3: 37 |
| descida | 6 | 1.483 | 1.5 | 0 | 274.4 | 365.1 | local-1: 3, local-2: 3, local-3: 3 |
| baixa | 132 | 0.35 | 0.348 | 0 | 277.1 | 316.6 | local-1: 15, local-2: 16, local-3: 15 |

## Scale-out (B)

Máximo de tasks: 3; final: 3. "Carga acima do alvo" é o momento em que a carga oferecida passa da CPU-alvo para as tasks existentes antes do degrau.

| Degrau | Carga acima do alvo | Alarme | Decisão | Task pronta | Alarme→pronta (s) | Decisão→pronta (s) | Carga→pronta (s) |
|---|---|---|---|---|---|---|---|
| sem scale-out observado | — | — | — | — | — | — | — |

## Scale-in (C)

Carga reduzida em 2026-11-13T02:19:27.075Z.

| Degrau | Alarme | Decisão | Desejadas reduzidas | Redução da carga→scale-in (s) | Alarme→scale-in (s) |
|---|---|---|---|---|---|
| sem scale-in observado | — | — | — | — | — |

Tempos medidos a partir do estado amostrado a cada 5 s (resolução da medição).

## Mesma carga, número de tasks diferente

Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. É a comparação entre uma e várias tasks sob a mesma carga oferecida.

| Fase | Oferecida (req/s) | Tasks saudáveis | Tempo (s) | Requisições | Vazão (req/s) | Erros (%) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| aquecimento | 0.517 | 3 | 12 | 6 | 0.5 | 0 | 316.3 | 335 |
| degrau-1 | 1.483 | 3 | 36 | 53 | 1.472 | 0 | 281.1 | 392.5 |
| degrau-2 | 2.617 | 3 | 42 | 110 | 2.619 | 0 | 297.9 | 405.5 |
| baixa | 0.35 | 3 | 132 | 46 | 0.348 | 0 | 277.1 | 316.6 |

## Linha do tempo

| UTC | Tipo | Descrição |
|---|---|---|
| 2026-11-13T02:17:44.579Z | k6_inicio | k6 iniciado (BC-escalabilidade) |
| 2026-11-13T02:21:43.823Z | k6_fim | k6 terminou (código 0) |
