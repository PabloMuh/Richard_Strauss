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

A configuração é feita apenas por variáveis de ambiente (`PORT`, padrão 8000, `APP_VERSION`, `WORK_DEFAULT_ITERATIONS`, `WORK_MAX_ITERATIONS`, `WORK_CONCURRENCY`, `KEEP_ALIVE_TIMEOUT`, padrão 75 s, `LOG_LEVEL`), o que permite usar a mesma imagem em todos os ambientes. O `KEEP_ALIVE_TIMEOUT` mantém as conexões ociosas abertas por mais tempo que o idle timeout do ALB (60 s); a seção "Erro 502 do ALB e ajuste do keep-alive" explica o motivo.

## Empacotamento

A imagem Docker parte de `python:3.12-slim`, instala dependências com versões fixas, executa como usuário não-root e define `HEALTHCHECK` em `/health`. Cada container roda um único processo, de modo que a capacidade do serviço depende apenas do número de tasks no ECS. A imagem é construída para `linux/amd64` e publicada no Amazon ECR pelo script de infraestrutura (`Publish-Image.ps1 -ContextPath ./app`) com tag fixa, registrando-se o digest utilizado nos testes.

## Validação

- 12 testes automatizados (pytest) cobrem as três rotas, o determinismo e o custo crescente de `/work`, a validação de parâmetros, o formato JSON dos erros, o limite de concorrência de `/work`, a resposta de `/health` com `/work` saturado e o keep-alive maior que o idle timeout do ALB.
- Duas instâncias da mesma imagem foram executadas localmente (portas 8081 e 8082 mapeadas para 8000), cada uma respondendo com seu próprio `instance_id` e produzindo o mesmo digest em `/work` (evidência em `app/docs/evidencias/duas-instancias.txt`).
- Calibração local: ~0,35 ms por 1.000 iterações (`iterations=100000` ≈ 37 ms no container).

## Reprodução

Ver `app/README.md`, seção "Reprodução".

## Execução na AWS (17/11/2026)

### Versões da imagem

As duas tags são imutáveis no ECR `richard-strauss` (`us-east-2`) e continuavam armazenadas em 24/11. Os digests foram conferidos no ECR e nos registros das tasks.

| Tag | Commit | Digest | Uso |
|---|---|---|---|
| `api-189bf27` | `189bf27` | `sha256:69fd745d5bd8607a276d99c6e69cbf97f846afa2240c9287f3c5ecb8b167ea71` | Deploy com 1 e 2 tasks (task definition rev. 1 e 2), smoke, calibração e o baseline anterior à correção |
| **`api-62f1e8e`** | `62f1e8e` | `sha256:922b1b43fc74cfb588c4da07e8f410a74c2dc4541744008fc68bd6db31633a15` | **Versão dos experimentos A, B/C e D** (task definition `richard-strauss-api:3`, fixada no digest) |

A versão `api-62f1e8e` alterou o keep-alive do Uvicorn de 5 s para 75 s. Como o código de `/work` permaneceu igual, os experimentos usaram a calibração de `api-189bf27` como referência de capacidade.

### Comportamento observado

- Duas tasks Fargate (0,25 vCPU, 512 MiB) atrás do ALB responderam com `instance_id` distintos (IDs das tasks lidos dos metadados ECS v4), em zonas diferentes, com distribuição de 15/15 em 30 requisições.
- **Custo de `/work` no Fargate:** `iterations=200000` (padrão) levou de 520 a 560 ms medidos pela própria API (`duration_ms`), cerca de 2,7 ms por 1.000 iterações, aproximadamente 8 vezes o custo local. Com `WORK_CONCURRENCY=1`, a calibração mediu vazão de **1,491 req/s** em uma task. Os experimentos adotaram **C = 1,50 req/s**. [Evidência da calibração](https://github.com/PabloMuh/Richard_Strauss/blob/629f0a7/tests/results/20261117-223019-calibracao-r1/resumo.md)
- Logs JSON por requisição no CloudWatch Logs, um stream por task (9 tasks na sessão). Os eventos expiraram com a retenção de 7 dias; restam os streams ([inventário de 24/11 no PR #6](https://github.com/PabloMuh/Richard_Strauss/pull/6)).
- `/health` manteve as tasks saudáveis durante toda a carga: nos experimentos não houve substituição de task por falha de health check, só as substituições provocadas pelo Auto Scaling e pela parada intencional do experimento D. Isso confirma a correção do API-02 no ambiente real.

### Erro 502 do ALB e ajuste do keep-alive

Na primeira execução do baseline A (`tests/results/pre-correcao/20261117-223742-A-baseline-r1`, imagem `api-189bf27`), **1 de 225 requisições (0,44%) recebeu HTTP 502**. As métricas do ALB mostram que o erro foi gerado pelo próprio balanceador (`HTTPCode_ELB_5XX_Count` = 1, `HTTPCode_Target_5XX_Count` = 0). [Evidência do baseline anterior ao ajuste](https://github.com/PabloMuh/Richard_Strauss/tree/629f0a7/tests/results/pre-correcao/20261117-223742-A-baseline-r1)

- **Causa provável.** O keep-alive de 5 s do Uvicorn era menor que o idle timeout de 60 s do ALB. Se o target fecha uma conexão enquanto o ALB aguarda a resposta de uma requisição, o balanceador pode retornar 502. [Diagnóstico de HTTP 502 na AWS](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html#http-502-issues)
- **Correção** (commit `62f1e8e`): `timeout_keep_alive` do Uvicorn configurável por `KEEP_ALIVE_TIMEOUT`, com padrão de 75 s, acima dos 60 s do ALB. Um teste automatizado impede que o padrão volte a ficar abaixo do idle timeout.
- **Verificação:** com `api-62f1e8e`, A, B/C e D somaram 3.036 requisições com **0 erros** no k6 e nenhum 5XX do ALB nas métricas exportadas. Houve uma execução de cada cenário com essa imagem.

A validação local usou conexão direta ao container. O 502 foi observado no baseline da AWS anterior ao ajuste.

Detalhes da implantação em [docs/deploy-aws-20261117.md](../../docs/deploy-aws-20261117.md).
