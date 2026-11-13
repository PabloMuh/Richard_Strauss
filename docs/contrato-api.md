# Contrato de integração com a pessoa 1

**Estado: confirmado pela pessoa 1 em 12/11/2026** (ver seção final). A proposta original segue abaixo.

## Entrega solicitada

- Repositório/pasta e commit da API, Dockerfile, contexto de build e comando de execução.
- Lista de variáveis obrigatórias e seus valores de exemplo sem segredos.
- Imagem Linux `amd64`, executável `python` disponível e servidor em `0.0.0.0:8000` (ou porta confirmada e atualizada no parâmetro `containerPort`).
- Logs de inicialização e requisições em stdout/stderr, com flush; a imagem deve funcionar como aplicação HTTP sem serviços de negócio externos.
- Previsão de entrega para permitir integração até 12/11.

## HTTP mínimo proposto

| Rota | Resposta esperada | Uso na infraestrutura |
|---|---|---|
| `GET /health` | HTTP 200 e JSON, ex. `{"status":"ok"}`; chamada rápida e sem trabalho pesado, **inclusive com `/work` ocupando a CPU da task** (API-02, resolvido em 12/11; ver [impedimentos](impedimentos.md)) | Health check interno (timeout 10 s) e target group (timeout 5 s) |
| `GET /instance` | HTTP 200, JSON com `instance_id` textual não vazio, ex. `{"instance_id":"hostname-da-task"}` | Distinguir réplicas; ID estável durante a vida do container e diferente em outra task |
| `GET /work` | HTTP 200 e JSON com os parâmetros padrão, trabalho CPU-bound limitado, resposta em até 15 s no smoke test | Teste breve agora; calibração da pessoa 3 na fase de carga |

O nome `instance_id` é uma proposta explícita adotada pelo smoke test. Se a pessoa 1 já usar outro contrato, alinhem e atualizem este documento e o script de teste juntos. O smoke test usa somente os parâmetros padrão de `/work`.

## Comprovação local da pessoa 1

Construir a imagem e executar dois containers em portas locais diferentes. Demonstrar `/health`, dois `instance_id` distintos, `/work` limitado e logs. Entregar comandos reproduzíveis. A pessoa 2 publica a imagem no ECR com tag fixa e registra seu digest antes do ECS.

## Confirmação da pessoa 1 — 12/11/2026

Entregue na branch `pessoa1/aplicacao`, pasta [`app/`](../app/README.md).

- **Contexto de build:** `app/` (Dockerfile em `app/Dockerfile`). Publicação: `./infrastructure/scripts/Publish-Image.ps1 -ContextPath ./app`.
- **Execução:** `python -m api` (CMD da imagem), servidor em `0.0.0.0:8000`. `containerPort` permanece **8000**; `python` disponível na imagem para o health check da task definition.
- **Imagem:** `python:3.12-slim`, Linux `amd64`, usuário não-root, sem serviços externos.
- **Variáveis:** nenhuma obrigatória, sem segredos. Opcionais: `PORT` (8000), `APP_VERSION`, `INSTANCE_ID`, `LOG_LEVEL` (INFO), `WORK_DEFAULT_ITERATIONS` (200000), `WORK_MAX_ITERATIONS` (5000000). `environment` da task pode ficar vazio.
- **Logs:** JSON, uma linha por requisição, em stdout sem buffer (`PYTHONUNBUFFERED=1`). `/health` não é logado.
- **Rotas:** contrato acima mantido sem alterações de nome. `/instance` retorna `instance_id` = ID da task ECS (via `ECS_CONTAINER_METADATA_URI_V4`), ou hostname fora do ECS. `/work` sem parâmetros leva ~60–75 ms localmente (muito abaixo do limite de 15 s); aceita `?iterations=N` para a calibração da pessoa 3.
- **Comprovação local:** `app/docs/evidencias/duas-instancias.txt` (dois containers, dois `instance_id`, `/work` limitado, logs) e 8 testes automatizados em `app/tests`.

**Atualização em 12/11/2026 (API-02, com o OK da pessoa 1):** `/health` passou a ser assíncrono e `/work` passou a executar no máximo `WORK_CONCURRENCY` cálculos simultâneos. É uma variável opcional, com padrão `1`, e os demais pedidos aguardam na fila. As rotas e os formatos de resposta não mudaram.
