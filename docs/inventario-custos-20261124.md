# Inventário final e custo da sessão de 17/11 — conta `7795****9628`

Responsável: Pessoa 1. Verificação em **25/11/2026 00:46 UTC** (24/11 21:46 BRT), região `us-east-2`, por AWS CloudShell e AWS CLI 2.42.3 (`aws login`, credencial temporária). Somente consultas de leitura. Fecha os dois itens pendentes de [`fechamento-infraestrutura.md`](fechamento-infraestrutura.md) referentes à conta de 17/11.

## Inventário final

| Recurso do projeto | Estado em 24/11 |
|---|---|
| Cluster ECS `richard-strauss`, serviço e tasks | Inexistentes (`ClusterNotFoundException`) |
| ALB, listener e target group | Nenhum na região |
| Application Auto Scaling (alvo e política do serviço) | Nenhum alvo ECS registrado |
| IPv4 público (ENIs) e Elastic IPs | Nenhum |
| Security groups com tag `Project=richard-strauss` | Nenhum |
| ECR `richard-strauss` | **Mantido**: `api-189bf27` e `api-62f1e8e` (~111 MB com manifestos de plataforma e atestações) |
| CloudWatch Logs `/ecs/richard-strauss` | **Mantido**, retenção de 7 dias. Os eventos de 17/11 já expiraram (0 eventos); restam 9 streams vazios |
| Role `ecsTaskExecutionRole` | Mantida (criada manualmente em 17/11, fora dos scripts) |

Os 9 streams (um por task) cobrem de **17/11 22:15 UTC a 18/11 00:39 UTC**. A última task parou às 00:39 UTC de 18/11, logo após o experimento D: a infraestrutura foi removida ao fim da sessão. A limpeza não foi registrada com o inventário `.state`, que ficou na máquina usada em 17/11; o estado acima é a evidência do encerramento.

## Custo da sessão (Cost Explorer, 16/11 a 24/11, diário)

| Serviço | Custo bruto (US$) | Dias com cobrança (UTC) |
|---|---:|---|
| Elastic Load Balancing | 0,0676 | 17 e 18/11 |
| Elastic Container Service (Fargate) | 0,0528 | 17 e 18/11 |
| VPC (IPv4 público das tasks) | 0,0470 | 17 e 18/11 |
| ECR (armazenamento) | 0,0012 | 17 a 24/11 |
| S3, Secrets Manager | < 0,0001 | dias isolados; não pertencem aos scripts do projeto |
| Glue, KMS, SNS, SQS, CloudWatch | 0,0000 | outros usos da conta, sem custo |
| **Total bruto** | **≈ 0,17** | |
| Créditos aplicados | −0,17 | mesmos dias |
| **Total líquido** | **0,00** | |

- Saldo do Free Plan após a sessão: **US$ 99,83 de US$ 100**, plano ativo até 17/05/2027.
- Cobrança de ECS, ELB e VPC apenas em 17 e 18/11; 18/11 corresponde às tasks e ao ALB ativos após 00:00 UTC.
- Cerca de 2,5 h de recursos para ≈ US$ 0,17, o que confirma a estimativa de planejamento de ~US$ 0,07/h com ALB e 2 tasks.
- Custo recorrente após a sessão: só o armazenamento do ECR, abaixo de US$ 0,01 por mês.

## Evidências brutas

Não versionadas porque contêm IDs da conta e das tasks. Ficam em `infrastructure/evidence/fechamento-20261124/` na máquina da Pessoa 1:

- `cost-explorer-20261116-20261124.json`: `get-cost-and-usage` por serviço e tipo de registro (uso e crédito).
- `account-plan-state.json`: saldo de créditos do Free Plan.
- `log-streams.json` e `logs-ecs-richard-strauss.json`: streams e eventos (vazio) do log group.
- `costs-console.csv`: exportação do console do Cost Explorer (custo líquido de créditos).
