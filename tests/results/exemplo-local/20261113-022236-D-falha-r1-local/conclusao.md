# Conclusão — D-falha (repetição 1, validação local)

## Hipótese

O ECS inicia uma task substituta e volta a 2 tasks saudáveis; a task restante absorve a carga e os erros ficam restritos ao momento da parada.

## Observação real

- 251 requisições, vazão de 1.383 req/s, p95 de 479.2 ms e 0.797% de erros.
- Fase `constante`: oferecida 1.4 req/s, alcançada 1.383 req/s, p95 479.2 ms, erros 0.797%.
- Réplica `api-1` parada com `docker compose stop`; recuperação em 35.0 s, dos quais 20 s são o atraso simulado da reposição.
- 2 erro(s) em 98 requisições na janela da falha; p95 de 549.9 ms antes, 479.2 ms durante e 414.2 ms depois.

## Limitações

- Ambiente local de `tests/local`: réplicas com 0,25 vCPU atrás de um nginx, sem ECS, ALB nem Auto Scaling.
- Tempos comprimidos por `-EscalaTempo`; estado amostrado a cada 5 s.
- Valida o script k6, o orquestrador e a análise; **não** é evidência dos experimentos na AWS.

## Próximos ajustes

- Executar na AWS conforme `tests/README.md`, com a capacidade medida no Fargate.
