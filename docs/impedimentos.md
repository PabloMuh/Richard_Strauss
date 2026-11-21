# Impedimentos e próximos passos — atualizado em 21/11/2026

| ID | Impedimento | Responsável / próxima ação | Impacto | Estado |
|---|---|---|---|---|
| AWS-01 | Validar acesso, região e permissões de implantação | Pessoa 2 | Libera o provisionamento | **Resolvido.** Deploy com uma task em 12/11 e deploy com ALB e duas tasks registrado em 17/11. [Fechamento de infraestrutura](fechamento-infraestrutura.md) |
| API-01 | API e Dockerfile não recebidos | Pessoa 1, com acompanhamento da pessoa 2: confirmar contrato e prazo | Bloqueia build, publicação e deploy da aplicação | **Resolvido em 12/11**: entregues em [`app/`](../app/README.md) e integrados |
| API-02 | Com `/work` ocupando a CPU, `/health` demora mais que o timeout do health check e o container fica `unhealthy` | Pessoa 1: tornar `/health` assíncrono e limitar a concorrência de `/work` | Bloqueia os experimentos de carga (13–19/11): o ECS substituiria tasks saudáveis durante o scale-out | **Resolvido em 12/11**: `/health` assíncrono e `/work` limitado a `WORK_CONCURRENCY` execuções simultâneas; medições em [validação local](validacao-local.md) |
| CUSTO-01 | Registrar custos e encerramento da sessão AWS de 17/11 | Pessoa 2 e titular da conta experimental | Fecha custos e limpeza no relatório | **Pendente.** A estimativa está documentada. Falta a confirmação do Billing e do inventário final na conta utilizada. [Fechamento de infraestrutura](fechamento-infraestrutura.md#custos-e-confirmação-pendente) |
| EXP-01 | Executar A, B, C e D com ALB e Auto Scaling e revisar as medições | Pessoas 2 e 3 | Libera os resultados para o relatório | **Executado em 17/11.** Há uma repetição de cada cenário. A pessoa 2 revisou os eventos do ECS e do Auto Scaling. A revisão experimental pela pessoa 3 segue pendente. [Evidências](https://github.com/PabloMuh/Richard_Strauss/tree/629f0a7/tests/results) |

Registre cada impedimento também como issue no GitHub, no mesmo dia, conforme o plano da equipe.

## Marcos

- **08/11:** modelos JSON, scripts, testes locais e documentação; registrar dependências.
- **09–10/11:** validar conta/orçamento, provisionar recursos autorizados e integrar imagem recebida.
- **10–11/11:** primeiro deploy com uma task, saúde e logs.
- **12/11:** validar duas réplicas, redeploy e evidências com pessoas 3 e 4.

Se uma dependência não chegar a tempo, atualize o impedimento no mesmo dia e revise a data com a equipe. Não marcar implantação ou validação AWS como concluída apenas pelos testes locais.
