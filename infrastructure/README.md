# Roteiro da Pessoa 2

Execute na raiz do repositório com **PowerShell 7.2+** (`pwsh`). Os scripts não usam o perfil AWS padrão implicitamente e não criam roles IAM, VPC, sub-redes, Internet Gateway ou NAT Gateway. A rede e a execution role precisam existir e ser autorizadas na conta.

## 1. Ferramentas e configuração

```powershell
./infrastructure/scripts/Setup-AwsCli.ps1
aws --version
./infrastructure/scripts/Test-Environment.ps1 -Offline
Copy-Item ./infrastructure/config.example.json ./infrastructure/config.local.json
```

O instalador baixa o MSI oficial para o usuário atual (`AWSCLIV2-User.msi`), valida a assinatura Authenticode da Amazon e instala silenciosamente, sem exigir instalação para todos os usuários. Não altera perfis nem credenciais. Abra um novo terminal após instalar.

Configure o acesso conforme a modalidade real da conta: use o mecanismo de login indicado pela instituição/SSO ou as credenciais temporárias do laboratório em um perfil dedicado. Sessões de laboratório podem exigir `aws_session_token` e expirar. Não transforme credenciais temporárias em chaves permanentes e não coloque credenciais neste repositório.

Se a conta utilizar IAM Identity Center e isso for indicado pelo administrador:

```powershell
aws configure sso --profile ecs-trabalho
aws sso login --profile ecs-trabalho
```

Em `config.local.json`, preencha primeiro `profile` e `region`. Consulte a identidade sem criar recursos:

```powershell
./infrastructure/scripts/Test-Environment.ps1
```

O relatório mostra o account ID da sessão. Confira-o no console e preencha `accountId` com os mesmos 12 dígitos. Uma conta diferente bloqueia as operações seguintes. Uma consulta permitida não comprova autorização para criar recursos nem para usar Fargate ou `iam:PassRole`.

## 2. Completar os parâmetros

| Campo | Preenchimento |
|---|---|
| `project` | Prefixo exclusivo de 3–24 caracteres, ex. `richard-strauss`; usado também como nome do cluster/ECR |
| `profile`, `region`, `accountId` | Perfil dedicado, região autorizada e conta conferida |
| `vpcId`, `subnetIds` | Rede existente; subnets com rota IPv4 `0.0.0.0/0` ativa para Internet Gateway |
| `executionRoleArn` | Role existente da conta, com trust para `ecs-tasks.amazonaws.com`, ECR e CloudWatch Logs |
| `useAlb` | `true` somente se ALB estiver permitido e incluído na estimativa; inicialmente `false` |
| `allowedCidrs` | Lista dos IPv4 públicos atuais dos participantes, cada um `/32`; restrição aplicada também ao ALB |
| `containerPort` | Porta acordada com a pessoa 1; proposta inicial `8000` |
| `imageTag` | Tag fixa por versão, por exemplo `api-a1b2c3d`; não usar `latest` |
| `desiredCount` | `1` para o primeiro deploy; `2` para a validação das réplicas |
| `environment` | Lista de objetos `name`/`value` textuais, somente configuração não sensível |
| `feasibility` | Marcar Fargate e PassRole como confirmados somente após verificar as restrições reais |
| `budget` | Responsável/referência do acordo, limite em USD, estimativa da sessão e fim da janela em ISO 8601 UTC |

Os valores iniciais de CPU, memória e retenção são `256`, `512` e `7`. São os únicos valores aceitos nesta primeira entrega. Para ALB, selecione subnets em pelo menos duas zonas distintas, com pelo menos oito endereços livres por subnet.

Exemplo da forma de registrar uma janela **depois** de obter os valores reais:

```json
"budget": {
  "approvedBy": "RESPONSAVEL_DO_ACORDO",
  "reference": "LINK_OU_REGISTRO_DA_DECISAO",
  "maxUsd": 0,
  "estimatedSessionUsd": 0,
  "sessionEndsAtUtc": ""
}
```

Zeros e campos vazios bloqueiam o provisionamento. Preencha com o orçamento e a estimativa reais. **Esses campos não limitam a fatura nem desligam recursos automaticamente.** A expiração da janela bloqueia novos provisionamentos/deploys, mas recursos ativos continuam cobrando. A limpeza permanece disponível após expiração.

## 3. Conferir os JSONs sem acessar a AWS

Depois de preencher os parâmetros estruturais, use um digest real ou um digest fictício apenas para preview:

```powershell
$previewDigest = '0' * 64
$previewImage = "CONTA.dkr.ecr.REGIAO.amazonaws.com/PREFIXO@sha256:$previewDigest"
# Substitua CONTA, REGIAO, PREFIXO e SG pelos dados da configuração.
./infrastructure/scripts/New-DeploymentFiles.ps1 -ImageUri $previewImage -SecurityGroupId 'sg-0123456789abcdef0'
```

Em modo ALB, passe também `-TargetGroupArn`. O comando gera os JSONs em `infrastructure/generated/preview`, sem chamada AWS. O arquivo de serviço do preview referencia a família; no deploy ele recebe o ARN exato da revisão registrada. Não implante arquivos com digest fictício ou tag `offline-preview`.

## 4. Provisionar

Somente após fechar viabilidade e orçamento:

```powershell
./infrastructure/scripts/Test-Environment.ps1
./infrastructure/scripts/Provision.ps1
```

Recursos: ECR privado com tags imutáveis, log group com retenção de sete dias, cluster ECS e security groups. Em modo ALB, também ALB, target group `ip` com `/health` e listener HTTP 80. As tasks têm IP público para saída; com ALB, a entrada na porta da aplicação aceita somente o SG do ALB. Sem ALB, aceita somente os `/32` configurados. A demonstração usa HTTP, sem dados sensíveis.

O inventário em `.state` é salvo após cada criação. Pode-se retomar um provisionamento parcial com o mesmo arquivo. Recursos de mesmo nome fora do inventário causam erro; não são adotados. Não execute operações concorrentes com o mesmo inventário. Não altere rede, porta, CIDRs ou modo ALB durante a vida dessa infraestrutura; para mudar esses campos, remova-a e depois reprovisione. Recursos remanescentes ou modificados manualmente exigem revisão.

## 5. Publicar a imagem da pessoa 1

Inicie Docker Desktop e confirme os testes locais da API antes de publicar. O Dockerfile deve conter o executável `python`, pois o health check usa a biblioteca padrão Python, sem depender de curl.

```powershell
./infrastructure/scripts/Publish-Image.ps1 -ContextPath 'C:\CAMINHO\DA\API' -Dockerfile 'Dockerfile'
```

O script constrói `linux/amd64`, autentica no ECR por stdin, publica a tag e registra o digest. A tag já existente não é sobrescrita. Para uma nova versão, altere `imageTag`; para reimplantar a mesma versão, execute apenas o deploy. O login Docker desse registry é encerrado ao final.

## 6. Implantar, observar e testar

```powershell
./infrastructure/scripts/Deploy.ps1
./infrastructure/scripts/Get-Status.ps1
./infrastructure/scripts/Test-Deployment.ps1
```

O deploy registra uma revisão da task definition fixada por digest, cria/atualiza o serviço e aguarda estabilização. O circuit breaker do ECS permite rollback de um redeploy malsucedido. Falha/timeout não exclui recursos: consulte os eventos e faça a limpeza ao encerrar.

`Get-Status` registra tasks, eventos, endpoints, health do target group, streams de logs e CPU/memória dos últimos 15 minutos. Métricas e timestamps de logs podem levar alguns minutos para aparecer. Caso a conta permita ECS mas negue leitura das métricas/logs, registre a restrição e ajuste as permissões antes de considerar a entrega concluída.

`Test-Deployment` consulta `/health`, `/instance` e `/work`, exige JSON HTTP 200, identifica `instance_id`, verifica saúde e existência de eventos no stream de cada task. Não gera carga contínua. Com ALB, tenta observar as duas réplicas em até 40 consultas adicionais de `/instance`; sem ALB, consulta cada IP público. O IP muda quando uma task é substituída. Não há endpoint único para distribuição de carga sem ALB.

Para demonstrar duas tasks, altere `desiredCount` para `2` e repita deploy/status/teste. Para demonstrar redeploy, publique uma nova tag e repita. Deploys com `maximumPercent=200` podem executar temporariamente até quatro tasks quando o desejado for dois: inclua a sobreposição na estimativa. O limite futuro de Auto Scaling ainda não está configurado.

## 7. Preservar evidências e encerrar

Guarde os JSONs de `evidence`, os JSONs efetivamente enviados em `generated`, o inventário e capturas do console com horário/região. Revise account IDs, ARNs, IPs e conteúdo dos logs antes de compartilhar. Nenhum segredo deve entrar em commits.

```powershell
# Revisão: lê a AWS, mas não remove recursos nem altera o inventário.
./infrastructure/scripts/Remove-Infrastructure.ps1 -WhatIf

# Remove serviço/tasks, ALB/listener/target group, SGs e cluster do inventário.
# Preserva ECR/imagens e logs, que ainda podem gerar cobrança de armazenamento.
./infrastructure/scripts/Remove-Infrastructure.ps1

# Após exportar evidências e decidir descartar os dados:
./infrastructure/scripts/Remove-Infrastructure.ps1 -DeleteStoredData
```

A remoção valida conta, região, inventário e tags de propriedade antes de agir. Não apaga rede/roles preexistentes. Deleções interrompidas preservam os registros pendentes e podem ser retomadas. Sem o inventário, não há exclusão automática. Confirme o estado no console e consulte o consumo: recursos criados manualmente não estão cobertos pelo script.

## Referências oficiais

- [Task definitions Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)
- [Execution role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)
- [Rede e saída para internet](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/networking-outbound.html)
- [Integração ECS/ALB](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/alb.html)
- [Instalação AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

## Verificações locais

```powershell
./infrastructure/tests/Test-Offline.ps1
# Opcional, com AWS CLI v2 e Node instalados; utiliza somente um servidor em loopback:
./infrastructure/tests/Test-Offline.ps1 -ValidateCliShapes
```

Os testes padrão cobrem sintaxe, configuração, conta divergente, orçamento, rede pública, propriedade por tags, renderização e inventário. A opção adicional testa os JSONs ECS com a CLI real apontando explicitamente para `127.0.0.1`, sem assinatura, credenciais ou chamadas AWS. Pode exigir liberação de loopback em ambientes com sandbox. O workflow do GitHub executa as verificações padrão, sem credenciais.
