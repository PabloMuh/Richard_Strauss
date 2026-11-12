# API — Pessoa 1 (aplicação, Docker e imagem)

API HTTP stateless em Python 3.12 (FastAPI + Uvicorn) para rodar em **várias tasks do Amazon ECS** e servir de alvo nos experimentos de carga. Esta pasta (`app/`) é o **contexto de build** da imagem.

## Contrato HTTP

Segue [docs/contrato-api.md](../docs/contrato-api.md). Respostas sempre `application/json`; toda resposta traz os headers `x-instance-id` e `x-request-id`.

| Método | Rota | Descrição | 200 OK (exemplo) |
|---|---|---|---|
| GET | `/health` | Health check do ECS/target group. Barato, sem dependências. | `{"status":"ok"}` |
| GET | `/instance` | Identifica a réplica. `instance_id` = ID da task no ECS (hostname fora dele), estável durante a vida do container. | `{"instance_id":"a1b2c3...","hostname":"ip-10-0-1-23","pid":1,"version":"3f9c2ab","started_at":"...","uptime_s":12.3,"ecs":{"task_arn":"...","task_id":"a1b2c3...","cluster":"...","family":"...","revision":"4","availability_zone":"us-east-1a"}}` |
| GET | `/work?iterations=N` | Trabalho **CPU-bound limitado**: N hashes SHA-256 encadeados. Custo linear em N; `digest` determinístico prova que o trabalho foi feito. | `{"instance_id":"...","iterations":200000,"digest":"a43f7d79...","duration_ms":63.2}` |

`iterations` é opcional (padrão `WORK_DEFAULT_ITERATIONS` = 200000, ~60–75 ms) e deve estar em `[1, WORK_MAX_ITERATIONS]`.

Erros (sempre JSON):

```json
{"error":{"code":"invalid_parameter","message":"query.iterations: ..."},"instance_id":"...","request_id":"..."}
```

| Status | `code` | Quando |
|---|---|---|
| 400 | `invalid_parameter` | `iterations` fora da faixa ou não inteiro |
| 404 | `not_found` | rota inexistente |
| 500 | `internal_error` | erro não tratado (logado com stack trace) |

Custo de referência (local, 1 núcleo): ~0,35 ms por 1.000 iterações. Recalibrar na vCPU do Fargate (256 CPU units) antes dos experimentos.

## Variáveis de ambiente

Nenhuma é obrigatória; não há segredos.

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `8000` | Porta HTTP; deve bater com `containerPort` em `infrastructure/config.local.json` |
| `APP_VERSION` | `dev` | Versão exibida em `/instance` (build-arg `APP_VERSION`) |
| `INSTANCE_ID` | — | Força o ID. Sem ele: ID da task ECS, ou hostname |
| `LOG_LEVEL` | `INFO` | Nível de log |
| `WORK_DEFAULT_ITERATIONS` | `200000` | Iterações quando `?iterations` não é informado |
| `WORK_MAX_ITERATIONS` | `5000000` | Limite superior aceito |
| `ECS_CONTAINER_METADATA_URI_V4` | injetada pelo ECS | Task ARN, cluster e AZ em `/instance` |

## Estrutura

```
app/
  api/
    main.py           rotas, middleware de log, handlers de erro JSON
    config.py         leitura/validação das variáveis de ambiente
    instance.py       identificação da réplica (metadados ECS v4)
    work.py           operação CPU-bound
    logging_setup.py  logs JSON em stdout (CloudWatch via awslogs)
    __main__.py       `python -m api` (lê PORT)
  tests/test_api.py   testes automatizados (pytest)
  Dockerfile          python:3.12-slim, usuário não-root, HEALTHCHECK
  docker-compose.yml  duas instâncias locais (8081, 8082)
  scripts/
    local_two_instances.sh  build + 2 containers + gera evidência
    smoke_test.sh           health + distribuição de respostas entre réplicas
  docs/
    relatorio-aplicacao.md  seção da aplicação no relatório
    evidencias/             saídas de execução
```

## Reprodução

Todos os comandos a partir de `app/`.

### 1. Sem Docker

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python -m api            # escuta em 0.0.0.0:8000
curl localhost:8000/health
curl localhost:8000/instance
curl "localhost:8000/work?iterations=200000"
```

### 2. Docker: duas instâncias locais

```bash
./scripts/local_two_instances.sh   # gera docs/evidencias/duas-instancias.txt
```

Equivalente manual:

```bash
docker build --build-arg APP_VERSION=local -t ecs-api:local .
docker run -d --name api-1 -p 8081:8000 -e INSTANCE_ID=api-1 ecs-api:local
docker run -d --name api-2 -p 8082:8000 -e INSTANCE_ID=api-2 ecs-api:local
curl localhost:8081/instance   # "instance_id":"api-1"
curl localhost:8082/instance   # "instance_id":"api-2"
docker logs api-1              # logs JSON
docker rm -f api-1 api-2
```

Ou `docker compose up --build`.

### 3. Publicação no ECR (com a Pessoa 2)

A publicação usa o script da infraestrutura, apontando para esta pasta como contexto (a partir da raiz do repositório, PowerShell 7.2+):

```powershell
./infrastructure/scripts/Publish-Image.ps1 -ContextPath ./app
```

O build é `linux/amd64`, compatível com a task definition (`X86_64`). Registre a URI e o digest resultantes em `docs/relatorio-aplicacao.md`.

### 4. Validar no ECS / ALB

```bash
./scripts/smoke_test.sh http://<endpoint>:8000 30
```

Mostra as respostas distribuídas entre os IDs das tasks.

## Decisões de projeto

- **Stateless**: nenhum estado local → qualquer task atende qualquer requisição.
- **Um processo por container**: escala horizontal pelo número de tasks no ECS, não por workers internos.
- **`/work` síncrono**: roda no threadpool do Uvicorn, sem bloquear o event loop; `/health` continua respondendo sob carga.
- **Logs**: uma linha JSON por requisição em stdout (sem buffer: `PYTHONUNBUFFERED=1`); `/health` não é logado para não poluir o CloudWatch.

## Problemas comuns

- **`permission denied ... docker.sock`**: usuário fora do grupo docker → `sudo usermod -aG docker $USER && newgrp docker`.
- **`Temporary failure in name resolution` no `pip install` do build (WSL)**: o DNS do WSL (`10.255.255.254`) não é acessível pelos containers →
  `echo '{ "dns": ["8.8.8.8", "1.1.1.1"] }' | sudo tee /etc/docker/daemon.json && sudo systemctl restart docker`.
