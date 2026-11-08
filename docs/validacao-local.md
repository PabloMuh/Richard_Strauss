# Validação local — 08/11/2026

## Verificado

- AWS CLI v2 **2.39.6** instalada para o usuário atual pelo MSI oficial com assinatura verificada.
- Docker CLI instalado; Docker Desktop Linux engine ainda não está em execução. Será necessário iniciá-lo ao receber a API.
- `Test-Offline.ps1 -ValidateCliShapes`: **30 casos aprovados**. Inclui 28 verificações locais e dois cenários da CLI real, com/sem ALB, usando servidor HTTP exclusivamente em loopback e sem credenciais.
- Sintaxe PowerShell, leitura dos JSONs e isolamento dos arquivos locais pelo `.gitignore` conferidos.
- Configuração local inicial criada sem perfil, região, account ID ou orçamento presumidos.

## Ainda não verificado

- Identidade, créditos e permissões efetivas da conta AWS do trabalho.
- Build/publicação da API da pessoa 1 e execução de containers locais.
- Criação real dos recursos, estabilidade ECS, HTTP, logs, redeploy e limpeza na AWS.

Não houve provisionamento nem consulta autenticada à AWS. Os testes locais validam a preparação e os controles; não comprovam que o laboratório autoriza a arquitetura. Os impedimentos permanecem em `impedimentos.md`.
