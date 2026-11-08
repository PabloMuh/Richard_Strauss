# Impedimentos e próximos passos — 08/11/2026

| ID | Impedimento | Responsável / próxima ação | Impacto |
|---|---|---|---|
| AWS-01 | Conta do projeto ainda precisa ser identificada/configurada e validada | Pessoa 2: preencher checklist e perfil/região/account ID | Bloqueia consultas reais e provisionamento |
| API-01 | API e Dockerfile não recebidos | Pessoa 1, com acompanhamento da pessoa 2: confirmar contrato e prazo | Bloqueia build, publicação e deploy da aplicação |
| CUSTO-01 | Limite de gastos e janela ainda não acordados | Equipe, com registro da pessoa 2 | Bloqueia criação de recursos cobrados |

Os artefatos locais podem avançar com os três impedimentos abertos. Copie estes registros para as issues do grupo quando o fluxo de trabalho estiver disponível; não foram criadas issues nem enviadas mensagens automaticamente.

## Marcos

- **08/11:** modelos JSON, scripts, testes locais e documentação; registrar dependências.
- **09–10/11:** validar conta/orçamento, provisionar recursos autorizados e integrar imagem recebida.
- **10–11/11:** primeiro deploy com uma task, saúde e logs.
- **12/11:** validar duas réplicas, redeploy e evidências com pessoas 3 e 4.

Se uma dependência não chegar a tempo, atualize o impedimento no mesmo dia e revise a data com a equipe. Não marcar implantação ou validação AWS como concluída apenas pelos testes locais.
