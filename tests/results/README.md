# Resultados dos experimentos

Cada execução de `tests/scripts/Invoke-Experiment.ps1` cria uma pasta `<AAAAMMDD-hhmmss>-<experimento>-r<n>/` aqui. O conteúdo de cada arquivo está descrito em [tests/README.md](../README.md#3-o-que-cada-execução-grava).

- **Antes de versionar:** revise os arquivos, preencha `conclusao.md` e confira que não há dados sensíveis. Os account IDs são mascarados automaticamente.
- **Tabela experimental:** com todas as execuções na AWS, gere `tabela-experimental.md`, `.csv` e `.json` nesta pasta:

```powershell
python tests/analysis/analisar.py consolidar tests/results
```

## exemplo-local/

Contém execuções de **validação local** do script k6, do orquestrador e da análise, feitas no ambiente de `tests/local`:

- 3 réplicas com 0,25 vCPU atrás de um nginx;
- sem ECS, ALB nem Auto Scaling;
- tempos comprimidos por `-EscalaTempo`.

Elas mostram o formato dos resultados e o comportamento esperado das ferramentas. **Não são evidência dos experimentos A–D**, que precisam ser executados na AWS. A tabela consolidada das execuções locais está em `exemplo-local/tabela-experimental.md`.
