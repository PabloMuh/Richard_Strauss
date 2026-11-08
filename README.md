# Richard Strauss — Sistemas Distribuídos / Amazon ECS

Preparação da **Pessoa 2: infraestrutura AWS e implantação**, com scripts PowerShell 7.2+, AWS CLI v2 e JSON versionado.

**Situação em 08/11/2026:** API/Dockerfile da pessoa 1 ainda não recebidos; conta do projeto pendente de identificação/configuração e validação; orçamento ainda não acordado. Nenhum recurso AWS foi provisionado nesta etapa.

## Começar agora

```powershell
# Na raiz do repositório, em PowerShell 7.2 ou superior:
./infrastructure/scripts/Test-Environment.ps1 -Offline
./infrastructure/tests/Test-Offline.ps1

# Cria sua configuração local, ignorada pelo Git. Não sobrescreva se já existir.
Copy-Item ./infrastructure/config.example.json ./infrastructure/config.local.json
```

1. Preencha o [checklist de viabilidade](docs/checklist-aws.md) ao configurar a conta do trabalho.
2. Alinhe o [contrato de integração](docs/contrato-api.md) com a pessoa 1.
3. Siga o [roteiro de infraestrutura](infrastructure/README.md) para configurar, provisionar, publicar, implantar e limpar.
4. Registre evidências e acompanhe os [impedimentos atuais](docs/impedimentos.md).

## Organização

- `infrastructure/templates`: modelos da task definition e do ECS service.
- `infrastructure/scripts`: validação, renderização local, provisionamento, publicação, deploy, consulta, teste HTTP e limpeza.
- `infrastructure/tests`: testes locais sem AWS, credenciais ou dependências de teste externas.
- `docs`: viabilidade, integração, arquitetura, custos e impedimentos.

Configuração local, inventário e evidências ficam ignorados pelo Git. Antes de compartilhar resultados, revise-os e copie somente o necessário para documentação versionada. Guarde uma cópia segura do inventário: a limpeza depende dele para comprovar a propriedade dos recursos.

Auto Scaling e experimentos de falha pertencem à etapa de 13–19/11 com a pessoa 3. Esta entrega prepara o deploy e a validação de uma ou duas tasks até 12/11.
