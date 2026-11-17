# Conclusão — smoke (repetição 1, validação local)

## Hipótese

As três rotas respondem HTTP 200 com JSON válido.

## Observação real

- 3 requisições, vazão de 2.262 req/s, p95 de 500.0 ms e 0.0% de erros.
- Checks do k6 aprovados (100%): `/health`, `/instance` e `/work` responderam como no contrato.

## Limitações

- Ambiente local de `tests/local`: réplicas com 0,25 vCPU atrás de um nginx, sem ECS, ALB nem Auto Scaling.
- Tempos comprimidos por `-EscalaTempo`; estado amostrado a cada 5 s.
- Valida o script k6, o orquestrador e a análise; **não** é evidência dos experimentos na AWS.

## Próximos ajustes

- Executar na AWS conforme `tests/README.md`, com a capacidade medida no Fargate.
