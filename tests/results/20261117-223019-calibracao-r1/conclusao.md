# Conclusão — calibracao (repetição 1)

Revisado pela Pessoa 3 em 25/11/2026 com `resumo.md`, `resumo-k6.json`, `timeline.csv` e `aws/`.

## Hipótese

Com a fila sempre ocupada, a vazão se estabiliza no limite de CPU de uma task.

## Observação real

- **Confirmada.** Quatro VUs mantiveram a fila cheia numa única task por cerca de 3 min: 283 requisições e 0 erros. A vazão estável, sem os 20 s iniciais, foi de **1,501 req/s**, e a média da execução, de 1,491 req/s (`resumo.md`, seção "Calibração"). A CPU ficou em 100% nos minutos inteiros (`aws/metricas-ecs-CPUUtilization.json`).
- O valor adotado para A, B/C e D foi **C = 1,50 req/s por task** (`capacidade_rps` no `metadata.json` dessas execuções).
- A latência alta é esperada (p50 de 2,5 s e p95 de 3,8 s): cada requisição espera atrás das outras três, porque a task executa um `/work` por vez (`WORK_CONCURRENCY=1`). Este cenário mede capacidade, não latência.
- Os experimentos seguintes confirmam C. A CPU média acompanhou a fração de C efetivamente oferecida: **48,7%** em A, com cerca de 0,48 C, e **81,7%** no degrau-1 de B/C, com cerca de 0,82 C. A carga efetiva foi 96% da planejada; ver "Ritmo do k6" nos `resumo.md` de A e B/C.

## Limitações

- Uma execução, com a imagem `api-189bf27`. O código de `/work` é o mesmo em `api-62f1e8e`, que só alterou o keep-alive.
- Medida com 0,25 vCPU, `WORK_CONCURRENCY=1` e 200000 iterações por `/work`. Mudar qualquer um desses valores exige nova calibração.
- A vazão é contada nos timestamps reais das respostas. Por isso o ritmo mais lento do k6 não a afeta: a calibração usa VUs constantes, sem plano de taxa.

## Próximos ajustes

- Nenhum para esta entrega.
