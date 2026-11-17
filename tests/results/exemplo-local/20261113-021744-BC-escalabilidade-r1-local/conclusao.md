# Conclusão — BC-escalabilidade (repetição 1, validação local)

## Hipótese

Em cada degrau a CPU passa de 60%, o alarme dispara e o serviço vai de 1 a 2 e de 2 a 3 tasks; sob a mesma carga, a latência cai com mais tasks. Com carga baixa, volta a 1 task após o alarme de scale-in (cerca de 15 min).

## Observação real

- 242 requisições, vazão de 1.018 req/s, p95 de 398.7 ms e 0.0% de erros.
- Fase `aquecimento`: oferecida 0.517 req/s, alcançada 0.5 req/s, p95 335.0 ms, erros 0.0%.
- Fase `subida-1`: oferecida 1.0 req/s, alcançada 1.0 req/s, p95 496.1 ms, erros 0.0%.
- Fase `degrau-1`: oferecida 1.483 req/s, alcançada 1.472 req/s, p95 392.5 ms, erros 0.0%.
- Fase `subida-2`: oferecida 2.05 req/s, alcançada 2.0 req/s, p95 398.7 ms, erros 0.0%.
- Fase `degrau-2`: oferecida 2.617 req/s, alcançada 2.619 req/s, p95 405.5 ms, erros 0.0%.
- Fase `descida`: oferecida 1.483 req/s, alcançada 1.5 req/s, p95 365.1 ms, erros 0.0%.
- Fase `baixa`: oferecida 0.35 req/s, alcançada 0.348 req/s, p95 316.6 ms, erros 0.0%.
- Distribuição entre as 3 réplicas fixas: local-1: 81, local-2: 81, local-3: 80. Sem Auto Scaling local, não há scale-out nem scale-in a medir.

## Limitações

- Ambiente local de `tests/local`: réplicas com 0,25 vCPU atrás de um nginx, sem ECS, ALB nem Auto Scaling.
- Tempos comprimidos por `-EscalaTempo`; estado amostrado a cada 5 s.
- Valida o script k6, o orquestrador e a análise; **não** é evidência dos experimentos na AWS.

## Próximos ajustes

- Executar na AWS conforme `tests/README.md`, com a capacidade medida no Fargate.
