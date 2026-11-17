# Checklist de viabilidade — Pessoa 2

Atualizado em **08/11/2026**; linha API/Dockerfile atualizada em **12/11/2026**. Situação inicial baseada na inspeção local e nas informações do integrante. Não há validação de permissões AWS enquanto a conta do trabalho não for configurada.

Use **permitido**, **bloqueado** ou **pendente** para cada capacidade. Guarde evidência e data de verificação. `Test-Environment.ps1` reporta consultas de leitura; criar um recurso exige permissões adicionais.

| Item | Estado | O que confirmar / evidência |
|---|---|---|
| Modalidade e identidade da conta | Pendente | Academy/Learner Lab ou própria, account ID, perfil dedicado e responsável |
| Créditos e vencimento | Pendente | Saldo real, período de validade e serviços cobertos; não presumir gratuidade |
| Região | Pendente | Região permitida; usar a mesma para ECR, ECS e logs |
| Credenciais e sessão | Pendente | Método de login, token temporário, duração e renovação |
| Orçamento do grupo | Pendente | Limite USD, estimativa, aprovador, registro e janela de uso |
| ECS/Fargate | Pendente | Criação de cluster, task definition, serviço e tasks Linux; quota/capacidade na região |
| ECR | Pendente | Criar/consultar repositório, autenticar, push/pull, consultar digest e tags |
| Execution role | Pendente | Role existente autorizada, trust ECS tasks, pull ECR e envio CloudWatch Logs |
| IAM PassRole | Pendente | Permissão do principal para passar especificamente essa role ao serviço ECS tasks |
| Service-linked role ECS | Pendente | Existência/autorização; necessária para operações ECS/rede/ALB conforme conta |
| VPC/subnets/Internet Gateway | Pendente | Rede existente e subnets com rota pública IPv4 ativa e endereços disponíveis |
| Security groups/tags | Pendente | Criar, consultar, autorizar regras restritas e excluir; ler tags para validar propriedade |
| CloudWatch Logs | Pendente | Criar grupo, definir retenção, consultar streams/eventos e excluir após exportação |
| CloudWatch Metrics | Pendente | Consultar CPU/memória de serviço ECS e preservar timestamps/unidades |
| ALB | Pendente | Permissões de criação/leitura/exclusão, duas AZs, tags, listener e target group IP; orçamento |
| Application Auto Scaling | Pendente | Registrar scalable target com tags, criar política de target tracking e desregistrar; service-linked role do Auto Scaling para ECS; leitura de atividades e histórico de alarmes |
| Limpeza | Pendente | Permissões de parar/deletar o serviço, ELB, SGs, cluster e dados próprios |
| API/Dockerfile | Entregue (12/11) | Em [`app/`](../app/README.md); build `linux/amd64` e duas réplicas validados localmente ([validação local](validacao-local.md)); comportamento sob carga corrigido (API-02) |

## Registro de verificação

Para cada item, anote: responsável, timestamp com fuso, região, estado, evidência/comando e restrição observada. Em caso de `AccessDenied`, registre a operação exata; não tente contornar as regras do laboratório nem criar outra conta para evitá-las.

Confirme as restrições no painel/instruções do laboratório ou com o administrador/docente. `iam:SimulatePrincipalPolicy`, se disponível, pode ajudar na investigação, mas não substitui a política efetiva da conta, SCPs e demais restrições. Os scripts não presumem permissão de criar roles IAM.

## Critério para avançar

- Identidade e região conferidas; conta com meios autorizados de uso dos recursos.
- Fargate e PassRole confirmados, rede pública adequada e execution role identificada.
- Estimativa e janela aprovadas de fato, registradas na configuração local.
- Recursos bloqueados documentados. Se Fargate estiver bloqueado, revisar a proposta com equipe/docente antes de escolher outra arquitetura.
- ALB bloqueado: usar inicialmente acesso individual às tasks e registrar que os testes de distribuição de carga precisam de solução aprovada.
