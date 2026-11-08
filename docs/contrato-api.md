# Contrato de integração — proposta para alinhar com a pessoa 1

**Estado: aguardando entrega e confirmação da pessoa 1.** Este documento é um roteiro para o integrante compartilhar; nenhuma mensagem foi enviada automaticamente.

## Entrega solicitada

- Repositório/pasta e commit da API, Dockerfile, contexto de build e comando de execução.
- Lista de variáveis obrigatórias e seus valores de exemplo sem segredos.
- Imagem Linux `amd64`, executável `python` disponível e servidor em `0.0.0.0:8000` (ou porta confirmada e atualizada no parâmetro `containerPort`).
- Logs de inicialização e requisições em stdout/stderr, com flush; a imagem deve funcionar como aplicação HTTP sem serviços de negócio externos.
- Previsão de entrega para permitir integração até 12/11.

## HTTP mínimo proposto

| Rota | Resposta esperada | Uso na infraestrutura |
|---|---|---|
| `GET /health` | HTTP 200 e JSON, ex. `{"status":"ok"}`; chamada rápida e sem trabalho pesado | Health check interno e target group |
| `GET /instance` | HTTP 200, JSON com `instance_id` textual não vazio, ex. `{"instance_id":"hostname-da-task"}` | Distinguir réplicas; ID estável durante a vida do container e diferente em outra task |
| `GET /work` | HTTP 200 e JSON com os parâmetros padrão, trabalho CPU-bound limitado, resposta em até 15 s no smoke test | Teste breve agora; calibração da pessoa 3 na fase de carga |

O nome `instance_id` é uma proposta explícita adotada pelo smoke test. Se a pessoa 1 já usar outro contrato, alinhem e atualizem este documento e o script de teste juntos. O smoke test usa somente os parâmetros padrão de `/work`.

## Comprovação local da pessoa 1

Construir a imagem e executar dois containers em portas locais diferentes. Demonstrar `/health`, dois `instance_id` distintos, `/work` limitado e logs. Entregar comandos reproduzíveis. A pessoa 2 publica a imagem no ECR com tag fixa e registra seu digest antes do ECS.
