# Fechamento de infraestrutura · Pessoa 2

O primeiro deploy em Fargate foi validado em 12/11/2026 com uma task em Ohio. Em 17/11, a pessoa 1 executou o deploy com ALB em outra conta e registrou o redeploy, a distribuição entre duas réplicas e os experimentos de escala e substituição. Este documento reúne a configuração usada e a revisão dos eventos de infraestrutura para o relatório.

| Sessão | Evidência e estado |
|---|---|
| 12/11 · conta `6300****4417` | Uma task saudável, três rotas com HTTP 200 e logs no CloudWatch. O serviço, o cluster e o grupo de segurança foram removidos ao fim do teste. A imagem `api-f8458a6` e o grupo de logs foram preservados. A estimativa bruta de US$ 0,10 e o limite operacional local de US$ 1 constam do registro da sessão. |
| 17/11 · conta `7795****9628` | O registro mostra as revisões 1 e 2 saudáveis e duas réplicas atendendo por um mesmo ALB. Os experimentos A, B/C e D registraram a revisão 3. O custo faturado e o desligamento após essa sessão ainda precisam de confirmação na conta experimental. |

[Registro de deploy e redeploy de 17/11](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/docs/deploy-aws-20261117.md) · [Evidências experimentais](https://github.com/PabloMuh/Richard_Strauss/tree/629f0a7/tests/results)

## Configuração efetivamente usada em 17/11

- Região `us-east-2` (Ohio), cluster `richard-strauss` e serviço `richard-strauss-api`. Tasks Fargate Linux x86_64 com 0,25 vCPU e 512 MiB, rede `awsvpc`, porta 8000 e a role de execução `ecsTaskExecutionRole`.
- VPC padrão com sub-redes públicas em duas zonas. O ALB recebeu HTTP na porta 80 e encaminhou para um target group de IPs na porta 8000, com health check em `/health` a cada 10 s, limiares de 2 e tempo de drenagem de 30 s. A aplicação enviou logs para `/ecs/richard-strauss`.
- Smoke e calibração usaram a tag `api-189bf27`. A, B/C e D usaram `api-62f1e8e` e a task definition `richard-strauss-api:3` fixada no digest `sha256:922b1b43fc74cfb588c4da07e8f410a74c2dc4541744008fc68bd6db31633a15`. Essa versão elevou o keep-alive do Uvicorn para 75 s.
- A rodou com uma task fixa. Em B/C, a política `richard-strauss-cpu` usou target tracking da CPU média do serviço, alvo de 60%, mínimo de uma task, máximo de três e cooldowns de 60 s para aumento e 180 s para redução. D rodou com duas tasks fixas após desativar a política.

[Metadados de B/C](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/tests/results/20261117-230132-BC-escalabilidade-r1/metadata.json) · [Política exportada](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/tests/results/20261117-230132-BC-escalabilidade-r1/aws/autoscaling-politicas.json)

## Revisão dos eventos do ECS e do Auto Scaling

| Cenário | O que as evidências sustentam |
|---|---|
| A · Baseline | Uma task e um alvo saudável ao longo da coleta. O k6 registrou 225 requisições, zero falhas e zero iterações descartadas na execução posterior à correção de keep-alive. |
| B · Aumento de escala | O Application Auto Scaling registrou decisões bem-sucedidas para 2 e 3 tasks. Da decisão até a primeira amostra com a quantidade correspondente de alvos saudáveis no ALB, passaram cerca de **35 s no 1→2** (23:10:50 → 23:11:25 UTC) e **30 s no 2→3** (23:13:50 → 23:14:20 UTC). |
| C · Redução de escala | O serviço voltou de 3 para 2 e depois para 1 task. A contagem desejada baixou cerca de **1.150 s** e **1.397 s** após o início da rampa de redução de carga, respectivamente. |
| D · Falha | Após o pedido de parada, uma task substituta apareceu na coleta em cerca de **37 s**. O ALB voltou a mostrar dois alvos saudáveis em **68 s**, e o k6 registrou zero erros nas 119 requisições da janela da falha. |

O resumo automático de B/C reaproveitou a primeira transição do alarme e a primeira decisão ao calcular o segundo degrau. Assim, os **210 s** contam desde o primeiro alarme até a terceira task saudável. Para comparar as decisões individuais, use os **35 s e 30 s** obtidos das atividades do Auto Scaling e da primeira amostra saudável do ALB. A coleta tem resolução nominal de 10 s. Houve uma repetição por cenário, então os tempos descrevem esta sessão.

[Atividades do Auto Scaling](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/tests/results/20261117-230132-BC-escalabilidade-r1/aws/autoscaling-atividades.json) · [Timeline B/C](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/tests/results/20261117-230132-BC-escalabilidade-r1/timeline.csv) · [Evidência da falha](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/tests/results/20261117-235404-D-falha-r1/resumo.md)

## Reprodução e encerramento

1. No checkout que inclui `62f1e8e`, configure o perfil da conta autorizada, região, duas sub-redes, role, `useAlb=true`, IPv4 permitidos e janela de uso. Valide com `Test-Environment.ps1`.
2. Execute `Provision.ps1`. Publique uma tag imutável com `Publish-Image.ps1 -ContextPath ./app` caso o digest ainda não esteja no ECR dessa conta. Se a imagem já estiver disponível, selecione sua tag na configuração local.
3. Execute `Deploy.ps1` e `Test-Deployment.ps1` com uma task. Para reproduzir a demonstração de duas réplicas, ajuste `desiredCount` para 2 e repita. Para um redeploy de código, publique uma nova tag e execute o deploy novamente. Registre a revisão, o digest e os IDs distintos devolvidos por `/instance` via ALB. Para a ordem de A, B/C e D, siga o roteiro de experimentos.
4. Salve as evidências e rode `Remove-Infrastructure.ps1 -WhatIf` com o perfil e o inventário da sessão. Execute a limpeza do projeto e confira novamente ECS, ALB e Application Auto Scaling. Registre separadamente o ECR e os logs preservados e o custo atribuído à sessão. Se o inventário estiver em outra máquina, use o original para conferir a propriedade dos recursos.

[Roteiro da infraestrutura](../infrastructure/README.md) · [Roteiro dos experimentos](../tests/README.md)

## Custos e confirmação pendente

Em 21/11, as consultas na conta `6300****4417` retornaram zero clusters ECS, zero ALBs do projeto e nenhum alvo cadastrado no Auto Scaling do serviço. O repositório ECR e o grupo de logs permaneceram. O Free Plan estava ativo com saldo de US$ 100. O saldo é um registro da conta e não discrimina o custo da sessão.

O registro de 17/11 estimou cerca de **US$ 0,07 por hora** com ALB e duas tasks. É um valor de planejamento. O custo da sessão depende do tempo de vida dos recursos, do número de tasks e IPv4 públicos, do uso de LCU, dos logs e do armazenamento de imagens. Os horários do k6 cobrem a janela medida, enquanto o ALB pode permanecer ativo antes e depois dessa janela. [Registro da sessão](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/docs/impedimentos.md) · [Preços do ALB](https://aws.amazon.com/elasticloadbalancing/pricing/) · [Preços de IPv4](https://aws.amazon.com/vpc/pricing/)

Para fechar o registro de 17/11, a pessoa 1 ou outro integrante com acesso à conta `7795****9628` precisa fornecer estas duas evidências:

- [ ] **Billing da sessão.** Registrar o intervalo consultado, o custo por serviço e os créditos aplicados. Se o Billing agregar outros usos no mesmo período, indicar essa limitação.
- [ ] **Inventário final da sessão.** Registrar a data da verificação, a ausência de tasks ativas, ALB e alvo do Auto Scaling do projeto, e quais imagens do ECR e grupos de logs foram mantidos.

[Como conferir a cobrança na AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/view-billing-dashboard.html)
