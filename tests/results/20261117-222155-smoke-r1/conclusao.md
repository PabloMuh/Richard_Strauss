# Conclusão — smoke (repetição 1)

Revisado pela Pessoa 3 em 25/11/2026 com `resumo.md`, `resumo-k6.json`, `timeline.csv` e `aws/`.

## Hipótese

As três rotas respondem HTTP 200 com JSON válido.

## Observação real

- **Confirmada.** O k6 fez 9 requisições (3 por rota: `/health`, `/instance` e `/work`), com 0 falhas e 100% dos checks (`resumo-k6.json`).
- O serviço tinha 2 tasks atrás do ALB, e as 3 respostas de `/work` vieram das duas (`446ef2ab…`: 1, `6c471c82…`: 2; `resumo.md`).
- `/work` teve p50 de 657 ms e máxima de 738 ms (`resumo.md`, só `/work`). O p95 de 706 ms citado em `docs/deploy-aws-20261117.md` é o do k6 para as três rotas juntas (`resumo-k6.json`).
- O ALB não registrou respostas 5XX (`aws/metricas-alb-HTTPCode_*`).

## Limitações

- Imagem `api-189bf27`, anterior à correção do keep-alive.
- Três chamadas a `/work` verificam o funcionamento, não o desempenho. A execução fica fora das comparações de latência.

## Próximos ajustes

- Nenhum. Rodar o smoke no início de cada nova sessão na AWS.
