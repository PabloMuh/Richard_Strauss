# Seção do relatório — Aplicação

## Objetivo

Fornecer uma API HTTP estável, stateless e reproduzível, executável em múltiplas tasks do Amazon ECS, que permita (i) verificar a saúde de cada task, (ii) identificar qual task atendeu cada requisição e (iii) gerar carga de CPU controlada para os experimentos de escalabilidade.

## Implementação

A API foi escrita em Python 3.12 com FastAPI e servida por Uvicorn. Expõe três rotas, todas com respostas JSON:

- **`GET /health`** — retorna `{"status":"ok"}`; usada pelo health check do target group do ALB e pelo `HEALTHCHECK` do container. É assíncrona e responde direto no event loop, mesmo com `/work` ocupando a CPU.
- **`GET /instance`** — retorna o identificador da instância, hostname, PID, versão, horário de início e tempo de atividade. No ECS, lê o endpoint de metadados v4 (`ECS_CONTAINER_METADATA_URI_V4`) e inclui task ARN, cluster, revisão da task definition e zona de disponibilidade. Permite observar o balanceamento entre tasks.
- **`GET /work?iterations=N`** — executa N aplicações encadeadas de SHA-256. A operação é CPU-bound, tem custo linear em N e produz um digest determinístico, que comprova que o processamento ocorreu. N é limitado por `WORK_MAX_ITERATIONS` e valores inválidos retornam HTTP 400.

O cálculo de `/work` roda numa thread separada do event loop, com no máximo `WORK_CONCURRENCY` (padrão 1) execuções simultâneas; os demais pedidos aguardam na fila sem consumir CPU. Na primeira versão, cada pedido ocupava uma thread própria. Com 0,25 vCPU, as threads disputavam a GIL do Python e, sob carga, `/health` ultrapassava o timeout do health check, o que levaria o ECS a substituir tasks saudáveis. Limitar a concorrência não reduz a vazão, porque o trabalho é CPU-bound e a task tem uma fração de um núcleo. A fila faz a latência de `/work` crescer com a carga, e é esse o efeito que o scale-out deve reduzir.

Toda resposta carrega os headers `x-instance-id` e `x-request-id`. Os logs são emitidos em JSON (uma linha por requisição) em stdout e coletados pelo CloudWatch Logs, contendo status, latência, instância e ID da requisição.

A configuração é feita apenas por variáveis de ambiente (`PORT`, padrão 8000, `APP_VERSION`, `WORK_DEFAULT_ITERATIONS`, `WORK_MAX_ITERATIONS`, `WORK_CONCURRENCY`, `LOG_LEVEL`), o que permite usar a mesma imagem em todos os ambientes.

## Empacotamento

A imagem Docker parte de `python:3.12-slim`, instala dependências com versões fixas, executa como usuário não-root e define `HEALTHCHECK` em `/health`. Cada container roda um único processo, de modo que a capacidade do serviço depende apenas do número de tasks no ECS. A imagem é construída para `linux/amd64` e publicada no Amazon ECR pelo script de infraestrutura (`Publish-Image.ps1 -ContextPath ./app`) com tag fixa, registrando-se o digest utilizado nos testes.

## Validação

- 11 testes automatizados (pytest) cobrem as três rotas, o determinismo e o custo crescente de `/work`, a validação de parâmetros, o formato JSON dos erros, o limite de concorrência de `/work` e a resposta de `/health` com `/work` saturado.
- Duas instâncias da mesma imagem foram executadas localmente (portas 8081 e 8082 mapeadas para 8000), cada uma respondendo com seu próprio `instance_id` e produzindo o mesmo digest em `/work` (evidência em `app/docs/evidencias/duas-instancias.txt`).
- Calibração local: ~0,35 ms por 1.000 iterações (`iterations=100000` ≈ 37 ms no container).

## Reprodução

Ver `app/README.md`, seção "Reprodução".

## Execução na AWS (17/11/2026)

- Imagem utilizada: `<conta>.dkr.ecr.us-east-2.amazonaws.com/richard-strauss:api-189bf27`, digest `sha256:69fd745d5bd8607a276d99c6e69cbf97f846afa2240c9287f3c5ecb8b167ea71`, construída do commit `189bf27` (tag imutável no ECR).
- Duas tasks Fargate (0,25 vCPU, 512 MiB) atrás do ALB responderam com `instance_id` distintos (IDs das tasks lidos dos metadados ECS v4), em zonas diferentes, com distribuição 15/15 em 30 requisições.
- Calibração de `/work` no Fargate: `iterations=200000` em 520–560 ms (~2,7 ms por 1.000 iterações), cerca de 8× o custo local.
- Logs JSON por requisição visíveis no CloudWatch Logs, um stream por task.
- Nenhum erro de aplicação na implantação e no smoke test. Detalhes: [docs/deploy-aws-20261117.md](../../docs/deploy-aws-20261117.md).

<!-- TODO: completar com erros de aplicação observados nos experimentos A–D, se houver -->
