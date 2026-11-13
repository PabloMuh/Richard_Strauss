# Testes de carga e experimentos — pessoa 3

Ferramentas para os experimentos A (baseline), B (scale-out), C (scale-in) e D (falha) do plano da equipe. Hipóteses, cargas e critérios estão no [plano de testes](plano-de-testes.md).

```
tests/
  load-test.js               gerador de carga (k6): smoke, calibracao, A-baseline, BC-escalabilidade, D-falha
  scripts/Invoke-Experiment.ps1   executa um experimento, coleta o estado do ECS/ALB e exporta métricas e eventos
  analysis/analisar.py       resumo, gráficos brutos e tabela experimental a partir dos arquivos coletados
  local/                     ambiente Docker sem AWS (3 réplicas com 0,25 vCPU + nginx no lugar do ALB)
  results/                   uma pasta por execução; exemplo-local/ traz execuções de validação
```

O Auto Scaling é configurado pelos scripts da infraestrutura (`Set-AutoScaling.ps1` e `Remove-AutoScaling.ps1`), descritos no [roteiro da infraestrutura](../infrastructure/README.md).

## Pré-requisitos

| Ferramenta | Para quê | Instalação |
|---|---|---|
| PowerShell 7.2+ | orquestrador e scripts AWS | `winget install --id Microsoft.PowerShell --source winget` |
| Docker Desktop | ambiente local e k6 (imagem `grafana/k6:1.0.0`, usada automaticamente se o `k6` não estiver instalado) | [docs.docker.com](https://docs.docker.com/desktop/) |
| Python 3.12 | análise e gráficos | `python -m venv tests/.venv` e `tests/.venv/Scripts/pip install -r tests/requirements.txt` |
| AWS CLI v2 e perfil do trabalho | só para os experimentos na AWS | ver o [roteiro da infraestrutura](../infrastructure/README.md) |

Passe o Python do ambiente virtual ao orquestrador com `-Python tests/.venv/Scripts/python.exe` (no Linux, `tests/.venv/bin/python`).

## 1. Validação local (sem AWS)

Confere o script k6, o orquestrador e a análise. Em B/C não há Auto Scaling local; as 3 réplicas ficam fixas. Os tempos podem ser comprimidos com `-EscalaTempo`.

```powershell
$py = 'tests/.venv/Scripts/python.exe'
./tests/scripts/Invoke-Experiment.ps1 -Local -Experimento smoke -Python $py
./tests/scripts/Invoke-Experiment.ps1 -Local -Experimento calibracao -EscalaTempo 0.5 -Python $py
# Use a vazão estável medida acima (resumo.md) como -CapacidadeRps:
./tests/scripts/Invoke-Experiment.ps1 -Local -Experimento A-baseline -CapacidadeRps 1.86 -EscalaTempo 0.3 -Python $py
./tests/scripts/Invoke-Experiment.ps1 -Local -Experimento BC-escalabilidade -CapacidadeRps 1.86 -EscalaTempo 0.1 -Python $py
./tests/scripts/Invoke-Experiment.ps1 -Local -Experimento D-falha -CapacidadeRps 1.86 -EscalaTempo 0.3 -Python $py
docker compose -f tests/local/docker-compose.yml down   # ao terminar
```

O ambiente local é criado na primeira execução e expõe o balanceador em `http://localhost:8080`. O CI (`.github/workflows/load-tests.yml`) roda os testes da análise e uma versão comprimida de `smoke` e `BC-escalabilidade` a cada mudança em `tests/` ou `app/`.

## 2. Roteiro na AWS

Pré-condições:

- Infraestrutura provisionada com `useAlb=true`.
- Imagem publicada e serviço implantado com `desiredCount=1`.
- `Test-Deployment.ps1` aprovado.
- Orçamento e janela registrados.
- Application Auto Scaling autorizado na conta (o `Test-Environment.ps1` consulta).

Combine a janela com o grupo: o roteiro completo usa cerca de 3 horas de ALB e de 1 a 3 tasks.

```powershell
$py = 'tests/.venv/Scripts/python.exe'

# 0. Teste de fumaça e calibração (1 task, sem Auto Scaling). A capacidade C vale para o resto do dia.
./tests/scripts/Invoke-Experiment.ps1 -Experimento smoke -Python $py
./tests/scripts/Invoke-Experiment.ps1 -Experimento calibracao -Python $py
$c = 0.0   # copie aqui a "Vazão estável" de tests/results/<calibracao>/resumo.md

# A. Baseline (1 task, sem Auto Scaling), 3 repetições
1..3 | ForEach-Object { ./tests/scripts/Invoke-Experiment.ps1 -Experimento A-baseline -CapacidadeRps $c -Repeticao $_ -Python $py }

# B + C. Escalabilidade (Auto Scaling 1 a 3 tasks, CPU-alvo 60%)
./infrastructure/scripts/Set-AutoScaling.ps1
1..3 | ForEach-Object { ./tests/scripts/Invoke-Experiment.ps1 -Experimento BC-escalabilidade -CapacidadeRps $c -Repeticao $_ -Python $py }

# D. Falha (2 tasks, sem Auto Scaling)
./infrastructure/scripts/Remove-AutoScaling.ps1 -DesiredCount 2
1..3 | ForEach-Object { ./tests/scripts/Invoke-Experiment.ps1 -Experimento D-falha -CapacidadeRps $c -Repeticao $_ -Python $py }

# Tabela experimental com todas as execuções e limpeza
& $py tests/analysis/analisar.py consolidar tests/results
./infrastructure/scripts/Remove-Infrastructure.ps1
```

**Como o orquestrador age:**

- **Condição inicial:** antes de cada execução, ele confere a condição inicial do experimento: serviço estável, número de tasks, Auto Scaling ativo ou não, e alvos saudáveis no ALB. Se ela não for atendida, recusa a execução e explica o motivo. Entre repetições de B/C, isso garante esperar o serviço voltar a 1 task.
- **Durante a carga:** registra o estado a cada 10 s e, em D, executa `stop-task` aos 3 minutos.
- **Depois da carga:** espera 3 minutos para o CloudWatch consolidar as métricas, exporta métricas, eventos e atividades e roda a análise.

Os account IDs são mascarados nos JSONs gravados.

**Se algo der errado:**

- Uma execução interrompida (Ctrl+C) para o k6, mas não altera recursos na AWS.
- Ao final da sessão, siga a limpeza do roteiro da infraestrutura, mesmo que os experimentos não tenham terminado.

## 3. O que cada execução grava

Pasta `tests/results/<AAAAMMDD-hhmmss>-<experimento>-r<n>/`:

| Arquivo | Conteúdo |
|---|---|
| `metadata.json` | Identificação e configuração: objetivo, hipótese, responsável, região, imagem, task definition, Auto Scaling, parâmetros do k6, horários UTC |
| `resumo-k6.json`, `k6-bruto.csv.gz`, `k6-log.txt` | Resumo do k6, uma linha por métrica de cada requisição (com fase e instância), avisos do k6 |
| `timeline.csv` | Tasks desejadas, em execução e saudáveis e alvos do ALB, a cada 10 s |
| `eventos.json` | Linha do tempo: início e fim do k6, `stop-task`, alarmes, decisões do Auto Scaling, eventos do ECS |
| `aws/*.json` | Respostas da AWS: métricas do CloudWatch (ECS e ALB), eventos, atividades, política, alarmes, tasks |
| `resumo.md`, `resumo.json`, `grafico-*.png` | Resultados calculados e gráficos brutos (gerados pela análise) |
| `conclusao.md` | Modelo para registrar a observação real, as limitações e os próximos ajustes |

Essas pastas cobrem o padrão de evidência do plano:

- **Identificação** e **configuração:** `metadata.json` e `resumo.md`.
- **Resultados:** k6, `timeline.csv`, `aws/` e gráficos.
- **Conclusão:** `conclusao.md`, preenchida pela equipe.

Revise o conteúdo antes de versionar.

Para recalcular a análise de uma pasta:

```powershell
& $py tests/analysis/analisar.py analisar tests/results/<pasta>
```

## 4. Executar o k6 sem o orquestrador

```bash
k6 run -e BASE_URL=http://<alb> -e CENARIO=A-baseline -e CAPACIDADE_RPS=1.8 \
  --out 'csv=fileName=k6-bruto.csv.gz,timeFormat=unix_milli' tests/load-test.js
```

| Variável | Valores |
|---|---|
| `CENARIO` | `smoke`, `calibracao`, `A-baseline`, `BC-escalabilidade` ou `D-falha` |
| `CAPACIDADE_RPS` | req/s de uma task, medidos no cenário `calibracao` |
| `ITERACOES` | iterações por `/work`; 0 usa o padrão do servidor |
| `ESCALA_TEMPO` | 1 = durações do plano |
| `VUS_MAX` | 300 |
| `TIMEOUT` | 60s |

Sem `timeline.csv` e `aws/`, a análise mostra só os resultados do k6.

## 5. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Pré-condições ... não atendidas" | Aguarde o serviço estabilizar ou ajuste o Auto Scaling e o número de tasks conforme a mensagem. `-IgnorarPrecondicoes` existe só para diferenças intencionais e fica registrado em `metadata.json` |
| `iteracoes_descartadas` > 0 no resumo | O k6 não teve usuários virtuais suficientes para a taxa planejada: aumente `VUS_MAX` ou verifique a máquina geradora |
| Alarme não dispara em B | Siga a seção 7 do plano de testes |
| Gráficos ausentes | Instale `tests/requirements.txt` no Python passado em `-Python` |
| O k6 não alcança o ambiente local | Com o k6 via Docker, o orquestrador usa a rede `rs-local_default`; suba o ambiente com `docker compose -f tests/local/docker-compose.yml up -d --wait` |
