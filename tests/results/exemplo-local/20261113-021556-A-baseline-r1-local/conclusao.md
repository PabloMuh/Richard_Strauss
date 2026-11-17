# Conclusão — A-baseline (repetição 1, validação local)

## Hipótese

Vazão igual à oferecida, latência estável, CPU próxima de 50% e nenhum erro.

## Observação real

- 77 requisições, vazão de 0.855 req/s, p95 de 330.6 ms e 0.0% de erros.
- Fase `constante`: oferecida 0.867 req/s, alcançada 0.856 req/s, p95 330.6 ms, erros 0.0%.

## Limitações

- Ambiente local de `tests/local`: réplicas com 0,25 vCPU atrás de um nginx, sem ECS, ALB nem Auto Scaling.
- Tempos comprimidos por `-EscalaTempo`; estado amostrado a cada 5 s.
- Valida o script k6, o orquestrador e a análise; **não** é evidência dos experimentos na AWS.

## Próximos ajustes

- Executar na AWS conforme `tests/README.md`, com a capacidade medida no Fargate.
