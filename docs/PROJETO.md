# Orquestração de containers com Amazon ECS — visão geral do projeto

**Disciplina:** Sistemas Distribuídos · **Tema 7:** Amazon ECS · **Equipe:** 4 integrantes · **Entrega final:** 01/12/2026
**Situação deste documento:** 25/11/2026, com base no histórico Git de todas as branches (`git log --all`).

> Este documento resume o projeto, as tecnologias, a contribuição de cada integrante e os resultados dos experimentos na AWS (17/11/2026, `us-east-2`, uma repetição por cenário, revisados em 25/11). Os números vêm dos arquivos indicados em cada seção.
>
> **Entregáveis da documentação:** [relatório técnico](relatorio-tecnico.pdf) · slides (deck de 12 slides, exportável para PPTX/PDF) · gerador do PDF: `python docs/gerar_pdfs.py`.

## 1. O que o projeto faz

O projeto implanta uma API HTTP simples em várias tasks do **Amazon ECS (Fargate)** e mede, com testes de carga reproduzíveis, três propriedades de sistemas distribuídos:

| Propriedade | Como aparece no projeto | Experimento |
|---|---|---|
| **Replicação** | Várias tasks atendem o mesmo serviço; `/instance` e o header `x-instance-id` mostram qual task respondeu | A (baseline) e distribuição de respostas |
| **Tolerância a falhas** | Com 2 tasks estáveis, uma é encerrada (`stop-task`) e o ECS inicia uma substituta | D (falha) |
| **Escalabilidade** | Target tracking de CPU a 60%, de 1 a 3 tasks, aumenta e reduz o serviço conforme a carga | B (scale-out) e C (scale-in) |

Banco de dados, interface web e funcionalidades de negócio estão fora do escopo (plano da equipe, seção 1).

## 2. Arquitetura

```mermaid
flowchart LR
  K[k6: gerador de carga] --> A[ALB: endereço único, health check /health]
  A --> S[ECS service: 1 a 3 tasks Fargate, 0,25 vCPU / 512 MiB]
  E[ECR: imagem por digest] --> S
  S --> L[CloudWatch Logs: logs JSON, 7 dias]
  S --> M[CloudWatch Metrics: CPU e memória]
  M --> AS[Application Auto Scaling: alvo de CPU 60%]
  AS --> S
```

- Linux x86_64, **0,25 vCPU e 512 MiB** por task; VPC existente, subnets públicas com IP público por task, **sem NAT Gateway**.
- Com ALB, as tasks só aceitam tráfego do security group do balanceador; sem ALB, apenas IPv4 `/32` dos participantes.
- Health check do target group a cada 10 s (2 acertos ou 2 falhas) e drenagem de 30 s, para não distorcer os tempos medidos.
- Auto Scaling: mínimo 1, máximo 3 tasks; cooldown de 60 s (scale-out) e 180 s (scale-in).

Fontes: [arquitetura-custos.md](arquitetura-custos.md), [infrastructure/templates/](../infrastructure/templates/), `Set-AutoScaling.ps1` e `Provision.ps1`.

## 3. Tecnologias utilizadas

| Camada | Tecnologia | Uso |
|---|---|---|
| Aplicação | Python 3.12, FastAPI 0.115.6, Uvicorn 0.34.0, AnyIO | API HTTP assíncrona |
| Testes da aplicação | pytest 8.3.4, httpx 0.28.1 | 12 testes automatizados |
| Container | Docker, imagem `python:3.12-slim` (~55 MB), usuário não-root | Empacotamento `linux/amd64` |
| Registro de imagens | Amazon ECR | Imagem com tag fixa e digest |
| Orquestração | Amazon ECS com Fargate, `awsvpc` | Service, task definition, tasks |
| Balanceamento | Application Load Balancer (opcional, recomendado) | Endereço único e health checks |
| Escala | Application Auto Scaling (target tracking `ECSServiceAverageCPUUtilization`) | Scale-out e scale-in |
| Observabilidade | CloudWatch Logs (`awslogs`) e CloudWatch Metrics | Logs JSON, CPU, memória, métricas do ALB |
| Automação | PowerShell 7.2+, AWS CLI v2 | Provisionar, publicar, implantar, testar, limpar |
| Carga | k6 1.0 (imagem `grafana/k6:1.0.0`) | Cenários smoke, calibração, A, B/C e D |
| Análise | Python, matplotlib 3.9.2 | Resumos, gráficos e tabela experimental |
| Ambiente local | Docker Compose, nginx | 3 réplicas atrás de um balanceador local |
| CI | GitHub Actions | Testes da app, checagens offline da infra e validação dos testes de carga |

## 4. Contribuição de cada integrante

A atribuição segue o plano da equipe (versão 1.0, 28/10/2026) e foi conferida nos commits. Todas as branches citadas foram mescladas em `main` até 25/11 (PRs #1 a #8).

### Pessoa 1 — Aplicação, Docker e imagem (`LandriAlencars`)

Commit `f8458a6` (12/11): API, Dockerfile e testes.

- **`GET /health`**: retorna `{"status":"ok"}`; usado pelo health check do container e do ALB.
- **`GET /instance`**: ID da task obtido do endpoint de metadados ECS v4 (ou hostname fora do ECS), versão, AZ, PID e uptime.
- **`GET /work?iterations=N`**: N hashes SHA-256 encadeados; operação CPU-bound, custo linear e digest determinístico. Padrão 200 000 iterações, máximo 5 000 000; valor inválido retorna 400.
- Respostas e erros sempre em JSON; headers `x-instance-id` e `x-request-id` em toda resposta.
- Logs JSON em stdout, uma linha por requisição (sem `/health`), coletados pelo CloudWatch.
- Configuração só por variáveis de ambiente, sem segredos: `PORT`, `APP_VERSION`, `INSTANCE_ID`, `LOG_LEVEL`, `WORK_DEFAULT_ITERATIONS`, `WORK_MAX_ITERATIONS` e, depois, `WORK_CONCURRENCY`.
- Evidência de duas instâncias locais com IDs distintos: [app/docs/evidencias/duas-instancias.txt](../app/docs/evidencias/duas-instancias.txt).
- Workflow de CI `.github/workflows/app.yml` (pytest e build da imagem).

Depois da integração:

- **`fbbdcca` (17/11)**: primeira implantação com ALB na conta experimental (`us-east-2`), com 1 e 2 tasks; correção do `Common.ps1` para achar o AWS CLI no Linux; calibração do `/work` no Fargate (~2,7 ms por 1 000 iterações). Registro: [deploy-aws-20261117.md](deploy-aws-20261117.md).
- **`62f1e8e` (17/11)**: keep-alive do Uvicorn de 5 s para 75 s (`KEEP_ALIVE_TIMEOUT`), corrigindo um HTTP 502 do ALB no primeiro baseline.
- **`629f0a7` (17/11)**: execução dos experimentos A, B/C e D na AWS. O resumo inicial foi gerado com ferramenta de IA e marcado como pendente de revisão; a Pessoa 3 o revisou em 25/11.
- **`7c9cc0a` e `05e5b02` (24/11)**: inventário final e custo da sessão ([inventario-custos-20261124.md](inventario-custos-20261124.md)) e seção da aplicação com os dados da AWS.

Detalhes: [app/README.md](../app/README.md) e [app/docs/relatorio-aplicacao.md](../app/docs/relatorio-aplicacao.md).

### Pessoa 2 — Infraestrutura AWS e implantação (`PabloMuh`)

Commit `551ed20` (08/11): preparação da infraestrutura. Commit `7d825ab` (12/11): formato correto das tags no ECR. PR #1 (`pessoa2/integracao`) mesclado em `main`.

- **Scripts PowerShell** em `infrastructure/scripts/`: `Setup-AwsCli`, `Test-Environment`, `New-DeploymentFiles`, `Provision`, `Publish-Image`, `Deploy`, `Get-Status`, `Test-Deployment` e `Remove-Infrastructure`, com funções comuns em `Common.ps1`.
- **Modelos versionados**: `task-definition.json` (Fargate, 256 CPU / 512 MiB, logs `awslogs`, health check) e `service.json`.
- **Controles de segurança e custo**: os scripts exigem conta conferida, orçamento e janela registrados; marcam os recursos com tags de propriedade e só removem o que comprovadamente criaram; não criam roles IAM, VPC nem NAT Gateway; não versionam credenciais.
- **Testes offline** (`infrastructure/tests/Test-Offline.ps1`) executados no GitHub Actions em Windows, sem acesso à AWS.
- **Documentação**: [checklist-aws.md](checklist-aws.md), [arquitetura-custos.md](arquitetura-custos.md), [contrato-api.md](contrato-api.md), [impedimentos.md](impedimentos.md) e o [roteiro da infraestrutura](../infrastructure/README.md).
- **`a681447`, `f52c6e1`, `9d99024` (21/11) e `eeb85fc`, `5821e2c`, `796162d` (25/11)**: primeiro deploy de 12/11 (uma task, conta `6300****4417`), revisão dos eventos do ECS e do Auto Scaling de 17/11, custos e inventário final em [fechamento-infraestrutura.md](fechamento-infraestrutura.md).

### Pessoa 3 — Auto Scaling, geração de carga e testes (`leonardo-lbp`)

Além dos experimentos, a Pessoa 3 fez as correções de integração que desbloquearam os testes de carga.

- **`f2d6cf3` (12/11)**: health check da task trocado de `urllib` por `socket` (`python -S`), com timeout de 10 s: o custo cai de ~0,30 s para ~0,10 s de CPU por execução. O deploy passa a definir `PORT` a partir de `containerPort` e `Publish-Image.ps1` grava `APP_VERSION` com a tag da imagem.
- **`d426ecd` (12/11)**, na área da Pessoa 1, com o OK dela: resolução do **impedimento API-02** (ver seção 5).
- **`cbc0b12` (12/11)**, em conjunto com a Pessoa 2: `Set-AutoScaling.ps1` e `Remove-AutoScaling.ps1` (target tracking de CPU, 1 a 3 tasks, alvo 60%); ajuste do health check do target group e da drenagem; testes offline ampliados para 35 casos.
- **`865b916` (12/11)**: experimentos.
  - `tests/load-test.js` (k6): cenários `smoke`, `calibracao`, `A-baseline`, `BC-escalabilidade` e `D-falha`.
  - `tests/scripts/Invoke-Experiment.ps1`: confere as pré-condições, roda o k6, registra o estado do ECS e do ALB a cada 10 s, executa o `stop-task` em D e exporta métricas, eventos e alarmes (account IDs mascarados).
  - `tests/analysis/analisar.py`: indicadores por fase, tempos de scale-out, scale-in e recuperação, gráficos e tabela experimental consolidada.
  - `tests/local/`: 3 réplicas com 0,25 vCPU e 512 MiB atrás de um nginx, para validar as ferramentas sem AWS.
  - `tests/plano-de-testes.md`: hipóteses, cargas, métricas, critérios e ameaças à validade.
- **`c8ce104` e `9f349ef` (25/11)**: revisão dos resultados da AWS contra os dados brutos. A análise passou a medir cada degrau pela própria decisão do Auto Scaling (2→3 em **30 s**, não 210 s), a CPU média só com minutos inteiros (A: 48,7%, não 37,7%) e a corrigir o ritmo do k6; conclusões em cada pasta e [RESUMO-AWS-20261117.md](../tests/results/RESUMO-AWS-20261117.md).

### Pessoa 4 — Observabilidade, pesquisa e documentação (`Matheus`)

- Este documento, o [relatório técnico](relatorio-tecnico.pdf), e os slides; o PDF é gerado por [gerar_pdfs.py](gerar_pdfs.py).
- Rastreabilidade: cada número citado indica o arquivo de origem; resultados locais são separados dos resultados na AWS.

## 5. Decisão técnica relevante: o impedimento API-02

Com 0,25 vCPU, vários cálculos de `/work` em paralelo disputavam a GIL do Python e atrasavam o `/health`. Sob carga, o health check falhava e o ECS substituiria tasks saudáveis no meio do scale-out.

| Situação (local, `docker --cpus 0.25`) | Falhas de `/health` (timeout 5 s) | Resultado |
|---|---|---|
| Antes: 20 clientes em `/work` por 60 s | 85% | Container `unhealthy` em 49 s |
| Depois: 20 clientes por 90 s | 0 de 90 | `/health` p50 86 ms, p95 186 ms; `/work` 1,81 req/s |
| Depois: 60 clientes por 60 s | 0 de 60 | `/health` p50 78 ms, p95 173 ms; `/work` 1,80 req/s |

**Correção:** `/health` assíncrono, respondendo direto no event loop; `/work` executado numa thread com no máximo `WORK_CONCURRENCY` (padrão 1) cálculos simultâneos, e os demais pedidos aguardam na fila sem consumir CPU. A vazão por task não muda (~1,8 req/s), mas a latência de `/work` cresce com a fila, e é esse o efeito que o scale-out deve reduzir. Fonte: [validacao-local.md](validacao-local.md).

## 6. Plano de experimentos

As cargas são frações de **C**, a vazão máxima de uma task, medida na calibração do mesmo dia: **C = 1,50 req/s no Fargate** (localmente, C ≈ 1,86 req/s).

| Experimento | Tasks | Carga | Mede |
|---|---|---|---|
| A · Baseline | 1, sem Auto Scaling | 0,5 C por 5 min | Vazão, latência p95, erros, CPU |
| B · Scale-out | 1 → 3 | 0,3 C; degraus de 0,85 C (6 min) e 1,5 C (7 min) | Alarme → task saudável no ALB, por degrau |
| C · Scale-in | 3 → 1 | 0,2 C por 22 min + 5 min de observação | Queda da carga → redução das tasks |
| D · Falha | 2, sem Auto Scaling | 0,8 C por 10 min; `stop-task` aos 3 min | Tempo de recuperação e erros na janela da falha |

Os degraus de B ficam abaixo da capacidade das tasks existentes, para que o experimento meça o Auto Scaling e não uma fila crescente. Detalhes: [tests/plano-de-testes.md](../tests/plano-de-testes.md).

## 7. Resultados na AWS (17/11/2026)

Região `us-east-2`, imagem `api-62f1e8e` (task definition rev. 3), ALB e Auto Scaling de 1 a 3 tasks, uma repetição por cenário. Fontes: [RESUMO-AWS-20261117.md](../tests/results/RESUMO-AWS-20261117.md) e [tabela-experimental.md](../tests/results/tabela-experimental.md).

| Experimento | Requisições | Erros | p50 / p95 | Resultado principal |
|---|---|---|---|---|
| Calibração | 283 | 0% | 2487 / 3829 ms (fila cheia) | **C = 1,50 req/s por task**, CPU a 100% |
| A · Baseline | 225 | 0% | 660 / 1014 ms | 1 task a ~0,48 C, CPU de 48,7% |
| B · Scale-out | 2091 (B+C) | 0% | 692 / 1301 ms | 1→2 e 2→3 em **35 s e 30 s** da decisão do Auto Scaling até a task saudável no ALB; **433 s** da carga acima do alvo até a 2ª task |
| C · Scale-in | (mesma execução) | 0% | — | 3→2 e 2→1 em **1108 s e 1348 s** após a queda da carga (~22 min), uma task por vez |
| D · Falha | 720 | 0% | 690 / 1106 ms | **68 s** até 2 tasks saudáveis; capacidade reduzida por ~31 s; **0 erros** nas 119 requisições da janela da falha |

- **Scale-out:** o ECS leva ~30–35 s para criar e registrar uma task; a reação completa é dominada pelo alarme (3 datapoints de 1 min acima de 60%).
- **Scale-in:** o alarme de baixa exige 15 datapoints abaixo de 54%, e a política retira uma task por vez com cooldown de 180 s.
- **Mesma carga, mais tasks:** com 1,5 C, passar de 2 para 3 tasks reduziu o p95 de 1392 para 1074 ms (−23%); com carga baixa, o p50 não muda.
- **Falha:** o `stop-task` é ordenado (o ECS tira o alvo do ALB e drena as conexões), e a task restante tinha folga; queda abrupta não foi testada.
- **Cauda periódica:** 4% a 10% das requisições passaram de 1 s, concentradas num ciclo de 30 s que coincide com o health check do container (causa provável, não testada isoladamente).
- **Erro corrigido:** o primeiro baseline teve 1 HTTP 502 do ALB em 225 requisições (keep-alive do Uvicorn de 5 s, menor que os 60 s do ALB). Depois da correção, foram 3036 requisições sem erro.

**Custos:** US$ 0,1686 brutos na sessão experimental (ELB 0,0676; Fargate 0,0528; IPv4 0,0470; ECR 0,0012), cobertos por créditos; saldo de US$ 99,83. Em 24/11, cluster, tasks, ALB, Auto Scaling, IPs e security groups já não existiam; ECR e logs foram mantidos. Fonte: [inventario-custos-20261124.md](inventario-custos-20261124.md).

### Validação local das ferramentas (13/11/2026)

Ambiente `tests/local`: 3 réplicas Docker com 0,25 vCPU atrás de nginx, **sem ECS, ALB nem Auto Scaling**, tempos comprimidos e 1 repetição por cenário. Validou o k6, o orquestrador e a análise antes da AWS; **não** é evidência dos experimentos.

| Execução | Vazão (req/s) | p95 (ms) | Erros | Observação |
|---|---|---|---|---|
| Smoke | 2,26 | 500,0 | 0% | — |
| Calibração | 1,74 | 3 890,6 | 0% | Fila sempre cheia, por desenho |
| A · Baseline | 0,85 | 330,6 | 0% | 1 réplica |
| B/C · Escalabilidade | 1,02 | 398,7 | 0% | 3 réplicas fixas |
| D · Falha | 1,38 | 479,2 | 0,8% | Recuperação em 35 s, dos quais 20 s são atraso simulado; 2 erros em 98 requisições na janela da falha |

Fonte: [tests/results/exemplo-local/tabela-experimental.md](../tests/results/exemplo-local/tabela-experimental.md).

## 8. Situação em 25/11 e limitações

| ID | Impedimento | Estado |
|---|---|---|
| AWS-01 | Conta, região e permissões | Resolvido: deploys em 12/11 e 17/11 |
| API-01 / API-02 | API entregue; `/health` sob carga | Resolvidos em 12/11 |
| CUSTO-01 | Custos e encerramento da sessão | Resolvido em 25/11 |
| EXP-01 | Experimentos A, B, C e D | Executados em 17/11 e revisados em 25/11; falta decidir sobre as repetições 2 e 3 |

Limitações: uma repetição por cenário (sem média nem desvio); gerador de carga numa máquina doméstica, com a latência incluindo a rede até `us-east-2`; só falha ordenada (`stop-task`). Fonte: [impedimentos.md](impedimentos.md).

## 9. Como reproduzir

```bash
# API sem Docker (a partir de app/)
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python -m api

# Duas instâncias com Docker
./scripts/local_two_instances.sh
```

```powershell
# Infraestrutura (raiz do repositório, PowerShell 7.2+)
./infrastructure/scripts/Test-Environment.ps1 -Offline
./infrastructure/tests/Test-Offline.ps1
```

O roteiro completo da AWS está em [infrastructure/README.md](../infrastructure/README.md); o dos experimentos, em [tests/README.md](../tests/README.md).

## 10. Referências

- Yerram, S. *AWS EKS vs AWS ECS: A Research-Based Comparison for Container Orchestration*. Zenodo, 2025. <https://zenodo.org/records/16500754>
- AWS. *What is Amazon ECS?* <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html>
- AWS. *Automatically scale your Amazon ECS service.* <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html>
