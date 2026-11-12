# Seção do relatório — Aplicação

## Objetivo

Fornecer uma API HTTP estável, stateless e reproduzível, executável em múltiplas tasks do Amazon ECS, que permita (i) verificar a saúde de cada task, (ii) identificar qual task atendeu cada requisição e (iii) gerar carga de CPU controlada para os experimentos de escalabilidade.

## Implementação

A API foi escrita em Python 3.12 com FastAPI e servida por Uvicorn. Expõe três rotas, todas com respostas JSON:

- **`GET /health`** — retorna `{"status":"ok"}`; usada pelo health check do target group do ALB e pelo `HEALTHCHECK` do container.
- **`GET /instance`** — retorna o identificador da instância, hostname, PID, versão, horário de início e tempo de atividade. No ECS, lê o endpoint de metadados v4 (`ECS_CONTAINER_METADATA_URI_V4`) e inclui task ARN, cluster, revisão da task definition e zona de disponibilidade. Permite observar o balanceamento entre tasks.
- **`GET /work?iterations=N`** — executa N aplicações encadeadas de SHA-256. A operação é CPU-bound, tem custo linear em N e produz um digest determinístico, que comprova que o processamento ocorreu. N é limitado por `WORK_MAX_ITERATIONS` e valores inválidos retornam HTTP 400.

Toda resposta carrega os headers `x-instance-id` e `x-request-id`. Os logs são emitidos em JSON (uma linha por requisição) em stdout e coletados pelo CloudWatch Logs, contendo status, latência, instância e ID da requisição.

A configuração é feita apenas por variáveis de ambiente (`PORT`, padrão 8000, `APP_VERSION`, `WORK_DEFAULT_ITERATIONS`, `WORK_MAX_ITERATIONS`, `LOG_LEVEL`), o que permite usar a mesma imagem em todos os ambientes.

## Empacotamento

A imagem Docker parte de `python:3.12-slim`, instala dependências com versões fixas, executa como usuário não-root e define `HEALTHCHECK` em `/health`. Cada container roda um único processo, de modo que a capacidade do serviço depende apenas do número de tasks no ECS. A imagem é construída para `linux/amd64` e publicada no Amazon ECR pelo script de infraestrutura (`Publish-Image.ps1 -ContextPath ./app`) com tag fixa, registrando-se o digest utilizado nos testes.

## Validação

- 8 testes automatizados (pytest) cobrem as três rotas, o determinismo e o custo crescente de `/work`, a validação de parâmetros e o formato JSON dos erros.
- Duas instâncias da mesma imagem foram executadas localmente (portas 8081 e 8082 mapeadas para 8000), cada uma respondendo com seu próprio `instance_id` e produzindo o mesmo digest em `/work` (evidência em `app/docs/evidencias/duas-instancias.txt`).
- Calibração local: ~0,35 ms por 1.000 iterações (`iterations=100000` ≈ 37 ms no container).

## Reprodução

Ver `app/README.md`, seção "Reprodução".

<!-- TODO: preencher após publicação/experimentos -->
- URI da imagem utilizada nos testes: `<IMAGE_URI>` (digest `<sha256>`)
- Calibração de `/work` na vCPU do Fargate: `<ms por 1.000 iterações>`
- Erros de aplicação observados durante os experimentos e correções: `<...>`
