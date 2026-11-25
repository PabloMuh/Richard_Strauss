# Primeira implantação na AWS — 17/11/2026

Responsável: Pessoa 1, com os scripts da Pessoa 2 (`infrastructure/scripts`). Executado em WSL2 (Ubuntu 24.04) com PowerShell 7.4.6 e AWS CLI 2.41.0. Account ID mascarado (`7795****9628`).

## Conta e restrições encontradas

- Conta com crédito de US$ 100, dentro de uma organização AWS com SCP (service control policy).
- **Somente `us-east-2` (Ohio) é permitida.** Em `us-east-1`, `us-west-1`, `us-west-2`, `sa-east-1` e `eu-west-1`, EC2 e ECS retornam *explicit deny* da SCP. Por isso a região do projeto é `us-east-2`.
- Em `us-east-2`, ECS, ECR, ELB, Application Auto Scaling, CloudWatch Logs/Metrics e IAM responderam às consultas (`Test-Environment.ps1`: todas permitidas; subnets e rotas válidas).
- A conta não tinha execution role. Foi criada `ecsTaskExecutionRole` (trust `ecs-tasks.amazonaws.com`, política gerenciada `AmazonECSTaskExecutionRolePolicy`, tag `Project=richard-strauss`), manualmente via CLI, pois os scripts não criam roles.
- Rede: VPC padrão, subnets públicas `us-east-2a` e `us-east-2b` (rota `0.0.0.0/0` para Internet Gateway). ALB habilitado (`useAlb=true`).

## Sequência executada (horários UTC)

| Etapa | Script | Resultado |
|---|---|---|
| Verificação | `Test-Environment.ps1` | Todas as consultas permitidas (22:12) |
| Provisionamento | `Provision.ps1` | ECR, log group `/ecs/richard-strauss`, cluster, SGs, ALB, target group e listener |
| Imagem | `Publish-Image.ps1 -ContextPath ./app` | `7795****9628.dkr.ecr.us-east-2.amazonaws.com/richard-strauss:api-189bf27`, digest `sha256:69fd745d5bd8607a276d99c6e69cbf97f846afa2240c9287f3c5ecb8b167ea71` (commit `189bf27`) |
| Deploy 1 task | `Deploy.ps1` (`desiredCount=1`) | Task definition rev. 1 estável |
| Teste 1 task | `Test-Deployment.ps1` | Aprovado: HTTP, saúde e streams de log (22:16) |
| Deploy 2 tasks | `Deploy.ps1` (`desiredCount=2`) | Rev. 2 estável, 2 tasks RUNNING e HEALTHY |
| Teste 2 tasks | `Test-Deployment.ps1` | Aprovado: duas réplicas observadas pelo ALB (22:20) |
| Smoke k6 | `Invoke-Experiment.ps1 -Experimento smoke` | 9 requisições, 0% de falhas, 100% dos checks, p95 706 ms (22:21) |
| Status | `Get-Status.ps1` | desired=2, running=2; eventos, métricas e streams registrados (22:22) |

## Observações

- **Distribuição pelo ALB:** 30 consultas a `/instance` → 15 para a task `446ef2ab…` (`us-east-2b`) e 15 para `6c471c82…`. `instance_id` = ID da task, lido dos metadados ECS v4; `version` = `api-189bf27`.
- **Custo de `/work` no Fargate (0,25 vCPU):** `iterations=200000` (padrão) levou **520–560 ms**, contra ~70 ms local. Cerca de **2,7 ms por 1.000 iterações**. A capacidade C de uma task deve ser medida na calibração da Pessoa 3 com esse hardware.
- **CloudWatch Logs:** um stream por task (`api/api/<task-id>`), com uma linha JSON por requisição (`msg=request`, `status`, `duration_ms`, `instance_id`).
- **CloudWatch Metrics:** `AWS/ECS CPUUtilization` do serviço disponível em intervalos de 1 min (média 3–15% em repouso/smoke).
- **Correção necessária para rodar fora do Windows:** `Get-AwsExecutable` (`Common.ps1`) falhava no Linux porque `$env:LOCALAPPDATA` não existe; corrigido para ignorar caminhos do Windows e usar o `aws` do PATH.

Evidências brutas (não versionadas, contêm IDs da conta): `infrastructure/evidence/` (environment, deploy, smoke, status) e `tests/results/20261117-222155-smoke-r1/`.
