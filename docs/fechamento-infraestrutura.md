# Fechamento de infraestrutura · Pessoa 2

O primeiro deploy em Fargate foi validado em 12/11/2026 com uma task em Ohio. Em 17/11, a pessoa 1 executou o deploy com ALB em outra conta e registrou o redeploy, a distribuição entre duas réplicas e os experimentos de escala e substituição. Este documento reúne a configuração usada e a revisão dos eventos de infraestrutura para o relatório.

| Sessão | Evidência e estado |
|---|---|
| 12/11 · conta `6300****4417` | Uma task saudável, três rotas com HTTP 200 e logs no CloudWatch. O serviço, o cluster e o grupo de segurança foram removidos ao fim do teste. A imagem `api-f8458a6` e o grupo de logs foram preservados. A estimativa bruta de US$ 0,10 e o limite operacional local de US$ 1 constam do registro da sessão. |
| 17/11 · conta `7795****9628` | As revisões 1 e 2 estabilizaram com uma e duas tasks, respectivamente. Os experimentos A, B/C e D usaram a revisão 3. O inventário de 24/11 registrou o encerramento dos recursos de execução e custo de cerca de US$ 0,17, coberto por créditos. [Custos e inventário final](#custos-e-inventário-final) |

[Registro de deploy e redeploy de 17/11](deploy-aws-20261117.md) · [Evidências experimentais](../tests/results/RESUMO-AWS-20261117.md)

## Configuração efetivamente usada em 17/11

- Região `us-east-2` (Ohio), cluster `richard-strauss` e serviço `richard-strauss-api`. Tasks Fargate Linux x86_64 com 0,25 vCPU e 512 MiB, rede `awsvpc`, porta 8000 e a role de execução `ecsTaskExecutionRole`.
- VPC padrão com sub-redes públicas em duas zonas. O ALB recebeu HTTP na porta 80 e encaminhou para um target group de IPs na porta 8000, com health check em `/health` a cada 10 s, limiares de 2 e tempo de drenagem de 30 s. A aplicação enviou logs para `/ecs/richard-strauss`.
- Smoke e calibração usaram a tag `api-189bf27`. A, B/C e D usaram `api-62f1e8e` e a task definition `richard-strauss-api:3` fixada no digest `sha256:922b1b43fc74cfb588c4da07e8f410a74c2dc4541744008fc68bd6db31633a15`. Essa versão elevou o keep-alive do Uvicorn para 75 s.
- A rodou com uma task fixa. Em B/C, a política `richard-strauss-cpu` usou target tracking da CPU média do serviço, alvo de 60%, mínimo de uma task, máximo de três e cooldowns de 60 s para aumento e 180 s para redução. D rodou com duas tasks fixas após desativar a política.

[Metadados de B/C](../tests/results/20261117-230132-BC-escalabilidade-r1/metadata.json) · [Política exportada](../tests/results/20261117-230132-BC-escalabilidade-r1/aws/autoscaling-politicas.json)

## Revisão dos eventos do ECS e do Auto Scaling

| Cenário | O que as evidências sustentam |
|---|---|
| A · Baseline | Uma task e um alvo saudável ao longo da coleta. O k6 registrou 225 requisições, zero falhas e zero iterações descartadas na execução posterior à correção de keep-alive. |
| B · Aumento de escala | O Application Auto Scaling registrou decisões bem-sucedidas para 2 e 3 tasks. Da decisão até a primeira amostra com a quantidade correspondente de alvos saudáveis no ALB, passaram cerca de **35 s no 1→2** (23:10:50 → 23:11:25 UTC) e **30 s no 2→3** (23:13:50 → 23:14:20 UTC). |
| C · Redução de escala | O serviço voltou de 3 para 2 e depois para 1 task. As decisões do Auto Scaling vieram cerca de **1.108 s** e **1.348 s** após o início da redução de carga, respectivamente. O instante da redução foi corrigido pelo ritmo do gerador de carga, que ficou 42 s atrás do plano nesse ponto. |
| D · Falha | Após o pedido de parada, uma task substituta apareceu na coleta em cerca de **37 s**. O ALB voltou a mostrar dois alvos saudáveis em **68 s**, e o k6 registrou zero erros nas 119 requisições da janela da falha. |

A primeira versão do resumo automático de B/C reaproveitava a primeira transição do alarme e a primeira decisão ao calcular o segundo degrau, e por isso mostrava **210 s**. A pessoa 3 corrigiu a análise em 25/11: cada degrau agora é medido a partir da própria decisão do Auto Scaling, e o resumo regenerado mostra os mesmos **35 s e 30 s** desta revisão. [Resumo revisado dos experimentos](../tests/results/RESUMO-AWS-20261117.md). A coleta tem resolução nominal de 10 s. Houve uma repetição por cenário, então os tempos descrevem esta sessão.

[Atividades do Auto Scaling](../tests/results/20261117-230132-BC-escalabilidade-r1/aws/autoscaling-atividades.json) · [Timeline B/C](../tests/results/20261117-230132-BC-escalabilidade-r1/timeline.csv) · [Evidência da falha](../tests/results/20261117-235404-D-falha-r1/resumo.md)

## Reprodução e encerramento

1. No checkout que inclui `62f1e8e`, configure o perfil da conta autorizada, região, duas sub-redes, role, `useAlb=true`, IPv4 permitidos e janela de uso. Valide com `Test-Environment.ps1`.
2. Execute `Provision.ps1`. Publique uma tag imutável com `Publish-Image.ps1 -ContextPath ./app` caso o digest ainda não esteja no ECR dessa conta. Se a imagem já estiver disponível, selecione sua tag na configuração local.
3. Execute `Deploy.ps1` e `Test-Deployment.ps1` com uma task. Para reproduzir a demonstração de duas réplicas, ajuste `desiredCount` para 2 e repita. Para um redeploy de código, publique uma nova tag e execute o deploy novamente. Registre a revisão, o digest e os IDs distintos devolvidos por `/instance` via ALB. Para a ordem de A, B/C e D, siga o roteiro de experimentos.
4. Salve as evidências e rode `Remove-Infrastructure.ps1 -WhatIf` com o perfil e o inventário da sessão. Execute a limpeza do projeto e confira novamente ECS, ALB e Application Auto Scaling. Registre separadamente o ECR e os logs preservados e o custo atribuído à sessão. Se o inventário estiver em outra máquina, use o original para conferir a propriedade dos recursos.

[Roteiro da infraestrutura](../infrastructure/README.md) · [Roteiro dos experimentos](../tests/README.md)

## Custos e inventário final

### Deploy de 12/11

Em 21/11, a consulta na conta `6300****4417` encontrou o repositório ECR e o grupo de logs preservados. Cluster ECS, ALB e alvo do Auto Scaling do projeto estavam ausentes. O Free Plan estava ativo com saldo de US$ 100. O custo de US$ 0,10 do primeiro deploy é uma estimativa da sessão.

### Sessão experimental de 17/11

Em **24/11/2026 às 21h46 BRT** (25/11 às 00h46 UTC), a pessoa 1 consultou a conta `7795****9628` em `us-east-2`. O inventário registra a ausência do cluster, serviço e tasks do projeto, do ALB e seus listeners e target group, dos alvos ECS no Auto Scaling, de IPv4 públicos associados e dos grupos de segurança do projeto.

Permaneceram as imagens `api-189bf27` e `api-62f1e8e` no ECR, o grupo `/ecs/richard-strauss` com retenção de sete dias e a role `ecsTaskExecutionRole`, criada manualmente. A consulta confirma o estado em 24/11. O horário exato da remoção e o estado das revisões da task definition ficaram fora do levantamento.

O Cost Explorer da conta informou os valores abaixo na consulta diária de **16 a 24/11**.

| Componente do projeto | Custo bruto (US$) |
|---|---:|
| Elastic Load Balancing | 0,0676 |
| ECS/Fargate | 0,0528 |
| VPC (IPv4 público) | 0,0470 |
| ECR (armazenamento no intervalo consultado) | 0,0012 |
| **Total** | **0,1686** |

O inventário informa **US$ 0,00 líquidos após créditos** e saldo de **US$ 99,83** no Free Plan na data da consulta. A estimativa de cerca de US$ 0,07 por hora com ALB e duas tasks serviu ao planejamento. Os dados brutos do Cost Explorer ficaram com a pessoa 1. [Inventário e custos da pessoa 1](inventario-custos-20261124.md)
