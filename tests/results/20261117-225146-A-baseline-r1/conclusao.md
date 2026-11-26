# Conclusão — A-baseline (repetição 1)

Revisado pela Pessoa 3 em 25/11/2026 com `resumo.md`, `resumo-k6.json`, `timeline.csv`, `eventos.json` e `aws/`.

## Hipótese

Vazão igual à oferecida, latência estável, CPU próxima de 50% e nenhum erro.

## Observação real

- **Confirmada.** Foram 225 requisições, com 0 erros e 0 iterações descartadas. O ALB contou 225 requisições e nenhuma resposta 5XX (`aws/metricas-alb-RequestCount.json` e `aws/metricas-alb-HTTPCode_*`). Uma task saudável o tempo todo.
- A vazão foi de 0,718 req/s, contra 0,75 req/s planejados. O k6 executou as 225 iterações do plano, mas 4% mais devagar que o relógio (fator de 1,040, carga efetiva de 96,2%; "Ritmo do k6" em `resumo.md`). A task acompanhou a carga que recebeu, sem formar fila.
- A CPU média ficou em **48,7%** nos minutos inteiros, com máxima de 58,1%, o que corresponde a cerca de 0,48 C. A primeira versão do resumo mostrava 37,7% porque incluía os minutos parciais do início e do fim.
- A latência típica foi estável, com p50 de 660 ms. O p95 de 1014 ms e o p99 de 2041 ms vêm de uma cauda de 5,8% de requisições acima de 1 s. Dessas, 69% começam na mesma faixa de 5 s de um ciclo de 30 s, contra cerca de 17% esperados ao acaso ("Cauda de latência por task" em `resumo.md`). A cauda é periódica e própria da task, não um efeito da carga. O ciclo coincide com o intervalo do health check do container (30 s em `infrastructure/templates/task-definition.json`), que inicia um interpretador Python dentro da task de 0,25 vCPU. Essa causa é provável, mas não foi testada isoladamente.

## Limitações

- Uma repetição.
- O gerador de carga roda numa máquina doméstica, e a latência inclui a rede até `us-east-2`.
- A carga efetiva foi 96% da planejada (ritmo do k6).
- O p95 do resumo usa o posto mais próximo (1014,4 ms); o resumo do k6 interpola (1011,9 ms).

## Próximos ajustes

- Para confirmar a causa da cauda: repetir A com o health check do container em intervalo maior e verificar se a fração acima de 1 s cai. Não é necessário para o relatório.
