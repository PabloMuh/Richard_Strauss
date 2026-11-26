# Conclusão — A-baseline antes da correção do keep-alive (repetição 1)

Revisado pela Pessoa 3 em 25/11/2026 com `resumo.md`, `k6-bruto.csv.gz` e `aws/`. A execução fica fora da tabela consolidada e serve de evidência do erro corrigido.

## Hipótese

Vazão igual à oferecida, latência estável, CPU próxima de 50% e nenhum erro.

## Observação real

- **Refutada pelo erro.** Uma de 225 requisições (0,44%) recebeu HTTP 502 em 156 ms, às 22:39:42 UTC. O ALB contou `HTTPCode_ELB_5XX_Count` = 1 e `HTTPCode_Target_5XX_Count` = 0: o 502 foi gerado pelo balanceador, sem resposta da aplicação (`aws/metricas-alb-*.json`).
- Fora o erro, o comportamento foi igual ao do A posterior: CPU de 49,1% nos minutos inteiros, p50 de 696 ms, p95 de 942 ms e 4,5% de requisições acima de 1 s. Dessas, 80% começam na mesma faixa de 5 s do ciclo de 30 s, como no A posterior.
- **Causa provável e correção.** O keep-alive do Uvicorn era de 5 s, menor que o idle timeout do ALB, de 60 s. O commit `62f1e8e` (imagem `api-62f1e8e`) passou o valor para 75 s (`KEEP_ALIVE_TIMEOUT`). Depois da correção, A, B/C e D somaram 3036 requisições sem erro e sem 5XX no ALB.

## Limitações

- Um único 502 não prova a causa. A evidência é indireta: 5XX do balanceador sem 5XX do alvo e nenhum novo 502 nas 3036 requisições seguintes. Explicação completa em `app/docs/relatorio-aplicacao.md`.

## Próximos ajustes

- Nenhum. A correção está na `main`.
