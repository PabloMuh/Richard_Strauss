# Conclusão — calibracao (repetição 1, validação local)

## Hipótese

Com a fila sempre ocupada, a vazão se estabiliza no limite de CPU de uma task.

## Observação real

- 159 requisições, vazão de 1.738 req/s, p95 de 3890.6 ms e 0.0% de erros.
- Vazão estável de uma réplica: **1.749 req/s**, usada como `-CapacidadeRps` nos demais exemplos.

## Limitações

- Ambiente local de `tests/local`: réplicas com 0,25 vCPU atrás de um nginx, sem ECS, ALB nem Auto Scaling.
- Tempos comprimidos por `-EscalaTempo`; estado amostrado a cada 5 s.
- Valida o script k6, o orquestrador e a análise; **não** é evidência dos experimentos na AWS.

## Próximos ajustes

- Executar na AWS conforme `tests/README.md`, com a capacidade medida no Fargate.
