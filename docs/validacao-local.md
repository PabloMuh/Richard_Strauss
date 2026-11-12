# Validação local

## 12/11/2026 — integração com a API da pessoa 1

Ambiente: Docker Desktop 28.3 (WSL2), PowerShell 7.4 e AWS CLI 2.40 em container Linux. Os limites do Fargate foram simulados com `docker run --cpus 0.25 --memory 512m`. Os números servem para comparar alternativas; não substituem medições no Fargate.

### Verificado

- Build `linux/amd64` de `app/`, como no `Publish-Image.ps1`: imagem de ~55 MB, usuário `appuser`, `python` em `/usr/local/bin`.
- Duas réplicas com 0,25 vCPU e 512 MiB e um endpoint de metadados ECS v4 simulado responderam corretamente:
  - `/health`, `/instance` (com `instance_id` igual ao ID da task) e `/work`;
  - erros 400 e 404 em JSON;
  - logs JSON em stdout, sem linhas de `/health`.
- Cada réplica ocupou ~36 MiB. O `/work` padrão (200.000 iterações) levou ~0,45 s.
- Task definition renderizada com `PORT=8000` e o novo health check:
  - as réplicas ficam `healthy`;
  - executado em forma exec, o comando retorna 0 com HTTP 200 e 1 com 404 ou com porta errada.
- `Test-Offline.ps1 -ValidateCliShapes`: **32 casos aprovados**, os 30 anteriores mais dois novos (tags no formato real de cada serviço e `PORT`). O teste de tags falha quando o `Assert-Owned` volta à versão anterior à correção de 12/11.

### Health check da task

| Comando (0,25 vCPU) | CPU por execução | Duração (ocioso) |
|---|---|---|
| Anterior: `python -c` com `urllib.request` | ~0,30 s | ~1,25 s |
| Atual: `python -S -c` com `socket` | ~0,10 s | ~0,46 s |

Medido com o `time` do bash dentro do container, 3 execuções de cada comando.

Também medimos sob carga: 20 clientes simultâneos em `/work` por 90 s, health check a cada 10 s e 3 tentativas. Para isolar o efeito do comando, usamos uma cópia local (não versionada) da API com a correção proposta para API-02.

| Comando | Timeout | Resultado |
|---|---|---|
| Anterior | 5 s | Container `healthy`, mas com falhas isoladas |
| Atual | 10 s | Nenhuma falha |

Para reproduzir a medição de custo:

```bash
docker build --platform linux/amd64 -t api:local app
docker run -d --name api --cpus 0.25 --memory 512m api:local
docker exec api bash -c 'time python -S -c "<comando de infrastructure/templates/task-definition.json>"'
```

### Impedimento API-02 (API atual)

Com 20 clientes simultâneos em `/work` por 60 s, **85% das consultas a `/health` com timeout de 5 s falharam**. Esse é o timeout padrão do target group do ALB.

- Com o health check anterior, o container ficou `unhealthy` em 49 s.
- Com o atual, chegou a 2 falhas seguidas, de 3 permitidas.

O ajuste da infraestrutura não resolve o problema: a correção precisa ser feita na API.

### Ainda não verificado

- Publicação no ECR, deploy e health checks reais no Fargate e no ALB.
- Comportamento sob carga depois da correção de API-02 na branch da pessoa 1.

## 08/11/2026 — preparação

### Verificado

- AWS CLI v2 **2.39.6** instalada para o usuário atual pelo MSI oficial com assinatura verificada.
- Docker CLI instalado; Docker Desktop Linux engine ainda não está em execução. Será necessário iniciá-lo ao receber a API.
- `Test-Offline.ps1 -ValidateCliShapes`: **30 casos aprovados**. Inclui 28 verificações locais e dois cenários da CLI real, com/sem ALB, usando servidor HTTP exclusivamente em loopback e sem credenciais.
- Sintaxe PowerShell, leitura dos JSONs e isolamento dos arquivos locais pelo `.gitignore` conferidos.
- Configuração local inicial criada sem perfil, região, account ID ou orçamento presumidos.

### Ainda não verificado

- Identidade, créditos e permissões efetivas da conta AWS do trabalho.
- Build/publicação da API da pessoa 1 e execução de containers locais.
- Criação real dos recursos, estabilidade ECS, HTTP, logs, redeploy e limpeza na AWS.

Não houve provisionamento nem consulta autenticada à AWS. Os testes locais validam a preparação e os controles; não comprovam que o laboratório autoriza a arquitetura. Os impedimentos permanecem em `impedimentos.md`.
