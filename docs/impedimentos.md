# Impedimentos e próximos passos — atualizado em 12/11/2026

| ID | Impedimento | Responsável / próxima ação | Impacto | Estado |
|---|---|---|---|---|
| AWS-01 | Conta do projeto ainda precisa ser identificada/configurada e validada | Pessoa 2: preencher checklist e perfil/região/account ID | Bloqueia consultas reais e provisionamento | Aberto (último registro: 08/11) |
| API-01 | API e Dockerfile não recebidos | Pessoa 1, com acompanhamento da pessoa 2: confirmar contrato e prazo | Bloqueia build, publicação e deploy da aplicação | **Resolvido em 12/11**: entregues em [`app/`](../app/README.md) e integrados |
| API-02 | Com `/work` ocupando a CPU, `/health` demora mais que o timeout do health check e o container fica `unhealthy` | Pessoa 1: tornar `/health` assíncrono e limitar a concorrência de `/work` | Bloqueia os experimentos de carga (13–19/11): o ECS substituiria tasks saudáveis durante o scale-out | **Resolvido em 12/11**: `/health` assíncrono e `/work` limitado a `WORK_CONCURRENCY` execuções simultâneas; medições em [validação local](validacao-local.md) |
| CUSTO-01 | Limite de gastos e janela ainda não acordados | Equipe, com registro da pessoa 2 | Bloqueia criação de recursos cobrados | Aberto (último registro: 08/11) |
| EXP-01 | Os experimentos B, C e D exigem ALB (`useAlb=true`) e Application Auto Scaling autorizados, mais cerca de 3 h de ALB com 1 a 3 tasks | Pessoas 2 e 3: confirmar permissões (`Test-Environment.ps1`) e incluir a sessão na estimativa; equipe aprova | Sem isso, só A e a calibração podem ser executados; ferramentas prontas e validadas localmente em [`tests/`](../tests/README.md) | Aberto (13/11) |

Registre cada impedimento também como issue no GitHub, no mesmo dia, conforme o plano da equipe.

## Marcos

- **08/11:** modelos JSON, scripts, testes locais e documentação; registrar dependências.
- **09–10/11:** validar conta/orçamento, provisionar recursos autorizados e integrar imagem recebida.
- **10–11/11:** primeiro deploy com uma task, saúde e logs.
- **12/11:** validar duas réplicas, redeploy e evidências com pessoas 3 e 4.

Se uma dependência não chegar a tempo, atualize o impedimento no mesmo dia e revise a data com a equipe. Não marcar implantação ou validação AWS como concluída apenas pelos testes locais.
