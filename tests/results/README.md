# Resultados dos experimentos

Cada execução de `tests/scripts/Invoke-Experiment.ps1` cria uma pasta `<AAAAMMDD-hhmmss>-<experimento>-r<n>/` aqui. O conteúdo de cada arquivo está descrito em [tests/README.md](../README.md#3-o-que-cada-execução-grava).

- **Antes de versionar:** revise os arquivos, preencha `conclusao.md` e confira que não há dados sensíveis. Os account IDs são mascarados automaticamente.
- **Tabela experimental:** com todas as execuções na AWS, gere `tabela-experimental.md`, `.csv` e `.json` nesta pasta:

```powershell
python tests/analysis/analisar.py consolidar tests/results
```

## Execuções na AWS (17/11/2026)

Uma repetição de cada cenário em `us-east-2`, revisada em 25/11. Resultados, interpretação e limitações estão em [RESUMO-AWS-20261117.md](RESUMO-AWS-20261117.md); os indicadores consolidados, em [tabela-experimental.md](tabela-experimental.md).

| Pasta | Cenário |
|---|---|
| `20261117-222155-smoke-r1` | Smoke com 2 tasks |
| `20261117-223019-calibracao-r1` | Calibração: C = 1,50 req/s por task |
| `20261117-225146-A-baseline-r1` | A · baseline |
| `20261117-230132-BC-escalabilidade-r1` | B · scale-out e C · scale-in |
| `20261117-235404-D-falha-r1` | D · falha |
| `pre-correcao/20261117-223742-A-baseline-r1` | Baseline anterior à correção do keep-alive, com um 502 do ALB. Fica fora da tabela consolidada |

Os `resumo.md` e a tabela são gerados por `tests/analysis/analisar.py`. Para refazê-los depois de mudar a análise, rode `analisar` em cada pasta e depois `consolidar`.

## exemplo-local/

Contém execuções de **validação local** do script k6, do orquestrador e da análise, feitas no ambiente de `tests/local`:

- 3 réplicas com 0,25 vCPU atrás de um nginx;
- sem ECS, ALB nem Auto Scaling;
- tempos comprimidos por `-EscalaTempo`.

Elas mostram o formato dos resultados e o comportamento esperado das ferramentas. **Não são evidência dos experimentos A–D**, que estão nas pastas da AWS acima. A tabela consolidada das execuções locais está em `exemplo-local/tabela-experimental.md`.
