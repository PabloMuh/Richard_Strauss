> ⚠️ **Feito pelo Claude (claudinho) — pendente de revisão da equipe.** Gerado automaticamente em 17/11/2026 a partir das execuções na AWS conduzidas com a Pessoa 1. Conferir números, interpretação e conclusões antes de usar no relatório.

# Conclusão — BC-escalabilidade (repetição 1)

Preencha depois de revisar `resumo.md` e os gráficos desta pasta.

## Hipótese

Em cada degrau a CPU passa de 60%, o alarme dispara e o serviço vai de 1 a 2 e de 2 a 3 tasks; sob a mesma carga, a latência cai com mais tasks. Com carga baixa, volta a 1 task após o alarme de scale-in (cerca de 15 min).

## Observação real

-

## Limitações

- Estado do serviço amostrado a cada 10 s; métricas do CloudWatch em períodos de 1 min.

## Próximos ajustes

-