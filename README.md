# Richard Strauss — Sistemas Distribuídos / Amazon ECS

Preparação da **Pessoa 2: infraestrutura AWS e implantação**, com scripts PowerShell 7.2+, AWS CLI v2 e JSON versionado.

**Situação em 12/11/2026:** API e Dockerfile da pessoa 1 integrados em [`app/`](app/README.md) e validados localmente ([validação local](docs/validacao-local.md)). O problema da API sob carga (API-02 em [impedimentos](docs/impedimentos.md)) foi corrigido no mesmo dia. Conta AWS, orçamento e provisionamento seguem o [checklist](docs/checklist-aws.md), cujo último registro é de 08/11/2026.

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
- `app`: API, Dockerfile e testes da pessoa 1 (contexto de build da imagem).
- `tests`: experimentos da pessoa 3 — script k6, orquestrador, análise, ambiente local e resultados ([README](tests/README.md), [plano de testes](tests/plano-de-testes.md)).
- `docs`: viabilidade, integração, arquitetura, custos e impedimentos.

Configuração local, inventário e evidências ficam ignorados pelo Git. Antes de compartilhar resultados, revise-os e copie somente o necessário para documentação versionada. Guarde uma cópia segura do inventário: a limpeza depende dele para comprovar a propriedade dos recursos.

Os experimentos de 13–19/11 (baseline, scale-out, scale-in e falha) estão preparados em [`tests/`](tests/README.md). O Auto Scaling é configurado por `infrastructure/scripts/Set-AutoScaling.ps1`. A execução na AWS depende do ALB e do orçamento da sessão (EXP-01 em [impedimentos](docs/impedimentos.md)).
