# Impedimentos e próximos passos — atualizado em 25/11/2026

| ID | Impedimento | Responsável / próxima ação | Impacto | Estado |
|---|---|---|---|---|
| AWS-01 | Validar acesso, região e permissões de implantação | Pessoa 2 | Libera o provisionamento | **Resolvido.** Deploy com uma task em 12/11 e com ALB e duas tasks em 17/11. A conta experimental permitia o provisionamento em `us-east-2`. [Registro de 17/11](deploy-aws-20261117.md) · [Fechamento](fechamento-infraestrutura.md) |
| API-01 | API e Dockerfile não recebidos | Pessoa 1, com acompanhamento da pessoa 2: confirmar contrato e prazo | Bloqueia build, publicação e deploy da aplicação | **Resolvido em 12/11**: entregues em [`app/`](../app/README.md) e integrados |
| API-02 | Com `/work` ocupando a CPU, `/health` demora mais que o timeout do health check e o container fica `unhealthy` | Pessoa 1: tornar `/health` assíncrono e limitar a concorrência de `/work` | Bloqueia os experimentos de carga (13–19/11): o ECS substituiria tasks saudáveis durante o scale-out | **Resolvido em 12/11**: `/health` assíncrono e `/work` limitado a `WORK_CONCURRENCY` execuções simultâneas; medições em [validação local](validacao-local.md) |
| CUSTO-01 | Registrar custos e encerramento da sessão AWS de 17/11 | Pessoa 2 e titular da conta experimental | Fecha custos e limpeza no relatório | **Resolvido em 25/11.** Cerca de US$ 0,17 brutos, cobertos pelos créditos. A consulta de 24/11 confirmou o encerramento dos recursos de execução. [Custos e inventário final](fechamento-infraestrutura.md#custos-e-inventário-final) |
| EXP-01 | Executar A, B, C e D com ALB e Auto Scaling e revisar as medições | Pessoas 2 e 3 | Libera os resultados para o relatório | **Executado em 17/11 e revisado em 25/11.** Há uma repetição de cada cenário. A pessoa 2 revisou os eventos do ECS e do Auto Scaling. A pessoa 3 conferiu os resultados com os dados brutos, corrigiu a medição do 2º degrau (30 s, não 210 s) e preencheu as conclusões. Falta decidir sobre as repetições 2 e 3. [Resumo revisado](../tests/results/RESUMO-AWS-20261117.md) |

Registre cada impedimento também como issue no GitHub, no mesmo dia, conforme o plano da equipe.

Para uma nova sessão AWS, a equipe deve registrar a janela e o limite de gastos acordados antes do provisionamento.

## Marcos

- **08/11:** modelos JSON, scripts, testes locais e documentação; registrar dependências.
- **09–10/11:** validar conta/orçamento, provisionar recursos autorizados e integrar imagem recebida.
- **10–11/11:** primeiro deploy com uma task, saúde e logs.
- **12/11:** validar duas réplicas, redeploy e evidências com pessoas 3 e 4.

Se uma dependência não chegar a tempo, atualize o impedimento no mesmo dia e revise a data com a equipe. Não marcar implantação ou validação AWS como concluída apenas pelos testes locais.
