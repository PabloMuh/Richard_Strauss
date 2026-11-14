"""Gera docs/relatorio-tecnico.pdf (Pessoa 4)."""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, KeepTogether, NextPageTemplate)
from reportlab.lib.fonts import addMapping

OUT, FIG = sys.argv[1], sys.argv[2]

L = "/usr/share/fonts/truetype/lato/"
pdfmetrics.registerFont(TTFont("Lato", L + "Lato-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Lato-Bold", L + "Lato-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Lato-Italic", L + "Lato-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Lato-BoldItalic", L + "Lato-BoldItalic.ttf"))
pdfmetrics.registerFont(TTFont("Lato-Heavy", L + "Lato-Heavy.ttf"))
pdfmetrics.registerFont(TTFont("Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
addMapping("Lato", 0, 0, "Lato"); addMapping("Lato", 1, 0, "Lato-Bold")
addMapping("Lato", 0, 1, "Lato-Italic"); addMapping("Lato", 1, 1, "Lato-BoldItalic")

NAVY = colors.HexColor("#1B3150"); TEAL = colors.HexColor("#0B7A70"); INK = colors.HexColor("#1F2A3D")
SOFT = colors.HexColor("#5A6575"); MIST = colors.HexColor("#EEF3F3"); LINE = colors.HexColor("#D5DDE0")
AMBER_BG = colors.HexColor("#FBEBDD"); AMBER = colors.HexColor("#7A3A08")

body = ParagraphStyle("body", fontName="Lato", fontSize=10.5, leading=15, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=3, spaceAfter=3, alignment=0)
h1 = ParagraphStyle("h1", fontName="Lato-Heavy", fontSize=17, leading=22, textColor=NAVY, spaceBefore=14, spaceAfter=8)
h2 = ParagraphStyle("h2", fontName="Lato-Bold", fontSize=12.5, leading=17, textColor=TEAL, spaceBefore=10, spaceAfter=5)
cell = ParagraphStyle("cell", fontName="Lato", fontSize=9, leading=12, textColor=INK)
cellh = ParagraphStyle("cellh", parent=cell, fontName="Lato-Bold", textColor=colors.white)
cap = ParagraphStyle("cap", fontName="Lato-Italic", fontSize=9, leading=12, textColor=SOFT, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
note = ParagraphStyle("note", fontName="Lato", fontSize=9.5, leading=13.5, textColor=AMBER)
ref = ParagraphStyle("ref", parent=body, fontSize=9.5, leading=13.5, leftIndent=14, firstLineIndent=-14, alignment=0)


def P(t, s=body): return Paragraph(t, s)
def B(items): return [Paragraph(i, bullet, bulletText="•") for i in items]
def code(t): return f'<font name="Mono" size="9">{t}</font>'


def table(rows, widths, zebra=True):
    data = [[Paragraph(c, cellh) for c in rows[0]]] + [[Paragraph(c, cell) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE), ("TOPPADDING", (0, 0), (-1, -1), 4),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if zebra:
        st += [("BACKGROUND", (0, i), (-1, i), MIST) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(st))
    return t


def box(t, bg=AMBER_BG):
    x = Table([[Paragraph(t, note)]], colWidths=[16 * cm])
    x.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return x


def fig(path, w, caption):
    img = Image(path); r = img.imageHeight / img.imageWidth
    img.drawWidth = w * cm; img.drawHeight = w * cm * r
    return KeepTogether([img, P(caption, cap)])


def decor(c, doc):
    c.saveState()
    c.setFont("Lato-Bold", 7.5); c.setFillColor(SOFT)
    c.drawRightString(A4[0] - 2.5 * cm, A4[1] - 1.4 * cm, "SISTEMAS DISTRIBUÍDOS  /  TEMA 7 — AMAZON ECS")
    c.setFont("Lato", 8)
    c.drawRightString(A4[0] - 2.5 * cm, 1.3 * cm, f"Relatório técnico • situação em 14/11/2026   |   Página {doc.page}")
    c.restoreState()


def cover(c, doc):
    c.saveState()
    c.setFillColor(NAVY); c.rect(0, A4[1] - 11 * cm, A4[0], 11 * cm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#8FD3C8")); c.setFont("Lato-Bold", 10)
    c.drawString(2.5 * cm, A4[1] - 3 * cm, "SISTEMAS DISTRIBUÍDOS  |  TEMA 7 — AMAZON ECS")
    c.setFillColor(colors.white); c.setFont("Lato-Heavy", 30)
    c.drawString(2.5 * cm, A4[1] - 5 * cm, "Orquestração de containers")
    c.drawString(2.5 * cm, A4[1] - 6.3 * cm, "com Amazon ECS")
    c.setFont("Lato", 13); c.setFillColor(colors.HexColor("#BFD8D5"))
    c.drawString(2.5 * cm, A4[1] - 7.8 * cm, "Relatório técnico parcial: arquitetura, implementação, método e")
    c.drawString(2.5 * cm, A4[1] - 8.5 * cm, "resultados de validação local")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.2 * cm, bottomMargin=2 * cm,
                      title="Relatório técnico — Orquestração de containers com Amazon ECS",
                      author="Equipe Richard Strauss — Pessoa 4 (documentação)", subject="Sistemas Distribuídos, Tema 7")
fr = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
frc = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 10 * cm, id="c")
doc.addPageTemplates([PageTemplate("capa", [frc], onPage=cover), PageTemplate("normal", [fr], onPage=decor)])

s = [NextPageTemplate("normal")]
s += [Spacer(1, 0.6 * cm), table([
    ["Disciplina", "Equipe", "Prazo final", "Data deste relatório"],
    ["Sistemas Distribuídos", "4 integrantes", "01/12/2026", "14/11/2026"]], [4.5, 3.5, 3.5, 4.5], zebra=False), Spacer(1, 0.8 * cm)]
s += [P("Resumo", h2), P(
    "Este relatório descreve o projeto do Tema 7: uma API HTTP containerizada, implantada como serviço replicado no "
    "Amazon ECS com Fargate, para demonstrar replicação, substituição automática de tasks após falha e escalabilidade "
    "automática por uso de CPU. São apresentados a fundamentação, a arquitetura, a implementação de cada frente da equipe, "
    "o método dos quatro experimentos (baseline, scale-out, scale-in e falha) e os resultados disponíveis até 14/11/2026. "
    "Nessa data, a aplicação, a infraestrutura como código, o Auto Scaling e as ferramentas de medição estavam prontos e "
    "validados localmente, mas nenhum recurso havia sido criado na AWS, por pendências de conta e orçamento. Por isso, todos "
    "os números aqui são de ambiente local e estão identificados como tal.")]
s += [Spacer(1, 0.3 * cm), box(
    "<b>Regra de leitura.</b> Nenhum número deste relatório foi estimado ou inventado. Cada valor indica o arquivo do "
    "repositório de onde foi tirado. Resultados locais (Docker com 0,25 vCPU) validam a aplicação e as ferramentas; "
    "não comprovam o comportamento no Fargate.")]
s += [PageBreak()]

# 1
s += [P("1. Introdução", h1), P(
    "Aplicações distribuídas precisam continuar disponíveis quando uma instância falha e acompanhar a variação de carga "
    "sem intervenção manual. Orquestradores de containers, como o Amazon Elastic Container Service (ECS), oferecem esses "
    "mecanismos de forma declarativa: o operador informa quantas cópias de uma aplicação devem existir e em que condições "
    "esse número muda, e o orquestrador mantém o estado desejado."),
    P("O objetivo da equipe é projetar, implantar e avaliar uma aplicação HTTP containerizada no ECS, demonstrando, com "
      "medições, três propriedades:"),
    *B(["<b>replicação de serviço</b>: várias tasks atendem o mesmo serviço e cada resposta identifica a task que a produziu;",
        "<b>tolerância a falhas</b>: ao encerrar uma task, o ECS inicia uma substituta e o serviço volta ao número desejado;",
        "<b>escalabilidade automática</b>: o número de tasks aumenta sob carga e diminui quando ela cai."]),
    P("Banco de dados, interface web e funcionalidades de negócio ficaram fora do escopo. A pilha escolhida foi FastAPI, "
      "Docker, Amazon ECR, Amazon ECS com Fargate, Application Load Balancer (ALB), CloudWatch e k6.")]

# 2
s += [P("2. Fundamentação", h1),
      P("2.1 Amazon ECS e Fargate", h2), P(
    "O Amazon ECS é um serviço gerenciado de orquestração de containers. Seus conceitos centrais são o <b>cluster</b> "
    "(agrupamento lógico), a <b>task definition</b> (especificação de imagem, CPU, memória, portas, logs e health check), a "
    "<b>task</b> (uma instância em execução da task definition) e o <b>service</b>, que mantém um número desejado de tasks "
    "(<i>desired count</i>) e, opcionalmente, as registra em um load balancer. Com o tipo de execução <b>Fargate</b>, a AWS "
    "provisiona a capacidade de computação de cada task, sem que a equipe administre instâncias EC2 [2]."),
      P("2.2 Serviço replicado e balanceamento", h2), P(
    "Replicar um serviço sem estado (stateless) permite que qualquer réplica atenda qualquer requisição. Um balanceador "
    "fornece um endereço único, distribui as requisições e retira de circulação as réplicas que falham no health check. "
    "No projeto, o ALB cumpre esse papel; sem ele, cada task teria um IP próprio que muda a cada substituição, o que "
    "impede medir scale-out e recuperação de forma contínua."),
      P("2.3 Tolerância a falhas", h2), P(
    "O ECS service compara continuamente o número de tasks em execução com o desejado. Quando uma task para, seja por falha, "
    "por health check reprovado ou por encerramento manual, o agendador inicia outra. O tempo de recuperação observado "
    "depende do início do container, do período de carência e dos parâmetros dos health checks; por isso esses parâmetros "
    "fazem parte da configuração registrada em cada experimento."),
      P("2.4 Escalabilidade automática", h2), P(
    "O Application Auto Scaling ajusta o desired count de um ECS service. Na política de <b>target tracking</b>, define-se "
    "um valor-alvo para uma métrica, aqui a CPU média do serviço, e o próprio serviço cria alarmes no CloudWatch que "
    "disparam o aumento ou a redução de tasks para aproximar a métrica do alvo [3]. Os cooldowns limitam a frequência das "
    "mudanças. A redução é, em geral, mais conservadora que o aumento, para evitar oscilação."),
      P("2.5 Trade-offs", h2),
      *B(["<b>Custo × disponibilidade</b>: mais tasks e um ALB aumentam a disponibilidade e a capacidade, mas cobram por hora.",
          "<b>Reatividade × estabilidade</b>: alvo de CPU baixo e cooldown curto reagem mais rápido, mas podem oscilar.",
          "<b>Simplicidade × controle</b>: Fargate dispensa gerenciar servidores, mas limita os tamanhos de task e o acesso ao host.",
          "<b>ECS × EKS</b>: o ECS é integrado à AWS e mais simples de operar; o EKS (Kubernetes) oferece portabilidade e um "
          "ecossistema maior, ao custo de mais complexidade operacional [1]."])]

# 3
s += [P("3. Arquitetura e implementação", h1), P(
    "O Quadro 1 resume a arquitetura projetada e versionada no repositório (" + code("docs/arquitetura-custos.md") + ", " +
    code("infrastructure/templates/") + ")."),
      table([["Componente", "Configuração"],
             ["Gerador de carga", "k6 1.0, modelo aberto (taxa de chegada fixa) contra GET /work"],
             ["Entrada", "ALB; health check /health a cada 10 s, 2 acertos ou 2 falhas; drenagem de 30 s"],
             ["ECS service", "Fargate, Linux x86_64, rede awsvpc, 1 a 3 tasks de 0,25 vCPU e 512 MiB"],
             ["Rede", "VPC existente, subnets públicas, IP público por task, sem NAT Gateway; tasks aceitam só o SG do ALB"],
             ["Imagem", "Amazon ECR, tag fixa por versão, task definition referencia o digest"],
             ["Observabilidade", "CloudWatch Logs (awslogs, retenção de 7 dias) e métricas AWS/ECS e AWS/ApplicationELB"],
             ["Auto Scaling", "Target tracking ECSServiceAverageCPUUtilization; alvo 60%; cooldown 60 s (out) e 180 s (in)"]],
            [3.6, 12.4]),
      P("Quadro 1 — Componentes da arquitetura proposta. Fonte: arquivos citados no texto.", cap),
      P("3.1 Aplicação (Pessoa 1)", h2), P(
    "A API foi escrita em Python 3.12 com FastAPI 0.115.6 e servida por Uvicorn 0.34.0 (" + code("app/") + "). É stateless e "
    "expõe três rotas, todas com respostas JSON; toda resposta traz os headers " + code("x-instance-id") + " e " +
    code("x-request-id") + "."),
      table([["Rota", "Comportamento", "Papel nos experimentos"],
             ["GET /health", "Retorna {\"status\":\"ok\"}; assíncrona, responde no event loop", "Health check do container e do ALB"],
             ["GET /instance", "ID da task (metadados ECS v4), versão, AZ, PID, uptime", "Distinguir réplicas"],
             ["GET /work?iterations=N", "N hashes SHA-256 encadeados; padrão 200 000, máximo 5 000 000; digest determinístico",
              "Carga de CPU controlada"]], [3.6, 7.4, 5.0]),
      Spacer(1, 6), P(
    "A imagem parte de " + code("python:3.12-slim") + ", roda como usuário não-root, tem cerca de 55 MB e é construída para "
    + code("linux/amd64") + ". A configuração é feita só por variáveis de ambiente, sem segredos. Os logs saem em JSON, uma "
    "linha por requisição, em stdout. Há 11 testes automatizados (pytest) e um workflow de CI que roda os testes e o build."),
      P("3.2 Infraestrutura (Pessoa 2)", h2), P(
    "Toda a infraestrutura é descrita por scripts PowerShell 7 e modelos JSON versionados (" + code("infrastructure/") + "), "
    "usando a AWS CLI v2. O ciclo cobre verificação do ambiente (" + code("Test-Environment") + "), provisionamento de ECR, "
    "cluster, security groups e ALB (" + code("Provision") + "), publicação da imagem (" + code("Publish-Image") + "), "
    "implantação (" + code("Deploy") + "), consulta, teste HTTP e limpeza (" + code("Remove-Infrastructure") + ")."),
      *B(["Os scripts recusam operar sem conta conferida, orçamento e janela registrados.",
          "Cada recurso recebe tags de propriedade e entra num inventário; a limpeza só remove o que comprovadamente foi criado.",
          "Não são criados roles IAM, VPC, sub-redes nem NAT Gateway; credenciais não são versionadas.",
          "35 casos de teste offline, executados no GitHub Actions sem acesso à AWS."]),
      P("3.3 Auto Scaling e experimentos (Pessoa 3)", h2), P(
    "Os scripts " + code("Set-AutoScaling.ps1") + " e " + code("Remove-AutoScaling.ps1") + " registram o serviço no "
    "Application Auto Scaling e criam ou removem a política de target tracking. As ferramentas de medição ficam em "
    + code("tests/") + ": o script k6 com os cenários, o orquestrador " + code("Invoke-Experiment.ps1") + " (pré-condições, "
    "k6, amostragem do ECS e do ALB a cada 10 s, " + code("stop-task") + " em D, exportação de métricas, eventos e alarmes) e "
    "a análise " + code("analisar.py") + ", que gera resumos, gráficos e a tabela experimental.")]

# 4 API-02
s += [P("4. Decisão técnica: o impedimento API-02", h1), P(
    "Na integração, a equipe verificou que, com 0,25 vCPU, vários cálculos de " + code("/work") + " em paralelo disputavam a "
    "GIL do Python e atrasavam o " + code("/health") + " além do timeout. Sob carga, o ECS consideraria a task doente e a "
    "substituiria, o que invalidaria os experimentos de escalabilidade. A Tabela 1 resume as medições locais antes e depois "
    "da correção."),
      table([["Situação (docker --cpus 0.25)", "Falhas de /health (timeout 5 s)", "/health p50 / p95", "Vazão de /work"],
             ["Antes: 20 clientes, 60 s", "85%", "—", "—"],
             ["Depois: 20 clientes, 90 s", "0 de 90", "86 / 186 ms", "1,81 req/s"],
             ["Depois: 60 clientes, 60 s", "0 de 60", "78 / 173 ms", "1,80 req/s"]], [5.4, 4.0, 3.3, 3.3]),
      P("Tabela 1 — Efeito da correção do API-02. Fonte: docs/validacao-local.md (12/11/2026).", cap), P(
    "A correção tornou " + code("/health") + " assíncrono e passou a executar " + code("/work") + " numa thread, com no "
    "máximo " + code("WORK_CONCURRENCY") + " (padrão 1) cálculos simultâneos; os demais pedidos esperam na fila sem consumir "
    "CPU. A vazão por task permanece em cerca de 1,8 req/s, e a latência de " + code("/work") + " passa a crescer com a fila, "
    "que é exatamente o efeito que o scale-out deve reduzir. O health check da task também foi trocado por um comando com "
    + code("socket") + ", que custa cerca de 0,10 s de CPU por execução, contra 0,30 s do anterior.")]

# 5 Metodologia
s += [P("5. Metodologia", h1), P(
    "Como " + code("/work") + " é limitado por CPU e cada task processa um cálculo por vez, a unidade de carga é <b>C</b>, a "
    "vazão máxima de uma task, medida no cenário de calibração no mesmo dia dos experimentos. Todas as cargas são frações "
    "de C, o que torna o plano independente do hardware. Localmente, C ≈ 1,86 req/s; no Fargate, C ainda precisa ser medido. "
    "Com carga L e N tasks, a CPU média é aproximadamente L / (N·C), e o target tracking busca N ≈ L / (0,6·C)."),
      table([["Experimento", "Tasks", "Carga", "Hipótese"],
             ["A · Baseline", "1, sem Auto Scaling", "0,5 C por 5 min", "Vazão ≥ 95% da oferecida, erros < 1%, CPU entre 35% e 65%"],
             ["B · Scale-out", "1 → 3", "0,3 C; degraus de 0,85 C (6 min) e 1,5 C (7 min)", "Desejadas 1→2→3 e p95 menor com mais tasks na mesma carga"],
             ["C · Scale-in", "3 → 1", "0,2 C por 22 min + 5 min", "Retorno a 1 task, erros < 1%"],
             ["D · Falha", "2, sem Auto Scaling", "0,8 C por 10 min; stop-task aos 3 min", "Substituta saudável no ALB; erros na janela < 1%"]],
            [2.8, 2.8, 4.8, 5.6]),
      P("Tabela 2 — Desenho experimental. Fonte: tests/plano-de-testes.md.", cap), P(
    "Os degraus de B ficam abaixo da capacidade das tasks existentes: com mais carga do que a capacidade, a fila cresceria "
    "sem limite e o experimento passaria a medir a fila, não o Auto Scaling. Os tempos são definidos assim:"),
      *B(["<b>Scale-out</b>: do alarme de alta entrar em ALARM até o ALB ter alvos saudáveis em número igual às novas tasks desejadas;",
          "<b>Scale-in</b>: do início da redução de carga até a redução das tasks desejadas;",
          "<b>Recuperação</b>: do pedido de stop-task até as tasks saudáveis voltarem ao número anterior."]),
      P("Indicadores coletados: vazão, latência p50/p95/p99, erros e distribuição por task (k6); tasks desejadas, em execução e "
        "saudáveis (ECS e ALB, a cada 10 s); CPU e memória (CloudWatch, períodos de 1 min); histórico de alarmes, atividades do "
        "Auto Scaling e eventos do ECS. A amostragem de 10 s e as métricas de 1 min limitam a precisão dos tempos. Estão "
        "previstas 3 repetições por cenário, se orçamento e prazo permitirem.")]

# 6 Resultados
s += [KeepTogether([P("6. Resultados disponíveis: validação local das ferramentas", h1), box(
    "<b>Atenção.</b> Os resultados abaixo vêm do ambiente " + code("tests/local") + ": 3 réplicas Docker com 0,25 vCPU e "
    "512 MiB atrás de um nginx, <b>sem ECS, ALB nem Auto Scaling</b>, com tempos comprimidos e uma repetição por cenário. "
    "Eles validam o k6, o orquestrador e a análise; não são evidência dos experimentos na AWS."), Spacer(1, 8),
      table([["Execução (13/11/2026)", "Vazão (req/s)", "p95 (ms)", "Erros", "Observação"],
             ["Smoke", "2,26", "500,0", "0%", "—"],
             ["Calibração", "1,74", "3 890,6", "0%", "Fila sempre cheia, por desenho"],
             ["A · Baseline", "0,85", "330,6", "0%", "1 réplica"],
             ["B/C · Escalabilidade", "1,02", "398,7", "0%", "3 réplicas fixas"],
             ["D · Falha", "1,38", "479,2", "0,8%", "Recuperação em 35 s (20 s simulados)"]], [4.0, 2.6, 2.3, 1.7, 5.4]),
      P("Tabela 3 — Execuções de validação local. Fonte: tests/results/exemplo-local/tabela-experimental.md "
        "(branch pessoa3/experimentos).", cap)]),
      fig(f"{FIG}/BC-esc-grafico-instancias.png", 16,
          "Figura 1 — Respostas por réplica no cenário BC-escalabilidade local (baldes de 30 s): as três réplicas fixas "
          "dividem a carga. Fonte: tests/results/exemplo-local/20261113-021744-BC-escalabilidade-r1-local/grafico-instancias.png."),
      fig(f"{FIG}/D-falh-grafico-carga-latencia.png", 15,
          "Figura 2 — Cenário D-falha local: vazão, carga oferecida, erros e latência (baldes de 10 s). A linha preta marca "
          "a parada da réplica e a verde, a recuperação. Fonte: tests/results/exemplo-local/20261113-022236-D-falha-r1-local/"
          "grafico-carga-latencia.png."),
      P("No cenário D local, houve 2 erros em 98 requisições na janela da falha, e o p95 foi de 549,9 ms antes, 479,2 ms "
        "durante e 414,2 ms depois da parada. Dos 35 s de recuperação, 20 s são o atraso de reposição simulado pelo script, "
        "pois não há ECS no ambiente local.")]

# 7 Discussão
s += [P("7. Discussão e limitações", h1),
      *B(["<b>Sem dados da nuvem.</b> Até 14/11, os impedimentos AWS-01 (conta), CUSTO-01 (orçamento e janela) e EXP-01 "
          "(ALB e Auto Scaling autorizados) estavam abertos. Nenhum tempo de scale-out, scale-in ou recuperação no ECS foi medido.",
          "<b>Mais tasks não provam desempenho.</b> As conclusões precisam relacionar o número de tasks à vazão, à latência e aos "
          "erros sob a mesma carga oferecida; a análise já separa as requisições pelo número de tasks saudáveis.",
          "<b>Fila sem limite na API.</b> Acima da capacidade, os pedidos esperam e os que passam de 60 s recebem 504 do ALB, mas "
          "continuam sendo processados. O desenho em degraus evita a situação; descartar excedentes seria uma melhoria futura.",
          "<b>Gerador fora da AWS.</b> A latência medida pelo k6 inclui a internet; o local de origem deve ser mantido entre repetições.",
          "<b>Variação do Fargate.</b> A CPU de 0,25 vCPU pode variar entre tasks e horários; por isso a calibração ocorre no mesmo dia.",
          "<b>Parâmetros dos health checks</b> (10 s, 2 acertos, drenagem de 30 s) influenciam os tempos e fazem parte da configuração."])]

# 8 Custos
s += [P("8. Custos e limpeza", h1), P(
    "Nenhum valor foi registrado porque região, créditos, janela e limite ainda não foram definidos. A estimativa deve ser "
    "feita na AWS Pricing Calculator considerando os componentes abaixo; o roteiro completo dos experimentos usa cerca de "
    "3 horas de ALB com 1 a 3 tasks."),
      table([["Componente", "Base de cobrança a considerar"],
             ["Fargate", "Horas de task × 0,25 vCPU e 0,5 GiB, incluindo inicialização e sobreposição de deploy"],
             ["IPv4 público", "IP-horas das tasks e do ALB"],
             ["ALB", "Horas do balanceador e unidades de capacidade"],
             ["ECR", "Armazenamento das imagens e transferências"],
             ["CloudWatch", "Ingestão e retenção de logs, métricas e alarmes"]], [3.6, 12.4]),
      P("Tabela 4 — Componentes de custo. Fonte: docs/arquitetura-custos.md.", cap), P(
    "Ao fim de cada sessão, os dados e as evidências são salvos e os recursos removidos com " + code("Remove-AutoScaling.ps1") +
    " e " + code("Remove-Infrastructure.ps1") + ". Reduzir o desired count a zero não remove ALB, repositório nem logs.")]

# 9 Equipe
s += [P("9. Contribuições da equipe", h1), P(
    "A divisão segue o plano da equipe e foi conferida no histórico Git de todas as branches. Os commits " + code("cbc0b12") +
    " e " + code("865b916") + " estão na branch " + code("pessoa3/experimentos") + ", ainda sem merge em " + code("main") + "."),
      table([["Integrante", "Responsabilidade", "Commits", "Entregas"],
             ["Pessoa 1 (LandriAlencars)", "Aplicação, Docker e imagem", "f8458a6", "API, Dockerfile, 8 testes, evidência de 2 instâncias, CI da app"],
             ["Pessoa 2 (PabloMuh)", "Infraestrutura AWS e implantação", "551ed20, 7d825ab", "Scripts, task definition, service, checklist, custos, impedimentos"],
             ["Pessoa 3 (leonardo-lbp)", "Auto Scaling, carga e testes", "f2d6cf3, d426ecd, cbc0b12, 865b916",
              "Health check leve, correção API-02, Auto Scaling, k6, orquestrador, análise"],
             ["Pessoa 4", "Observabilidade e documentação", "pessoa4/documentacao", "docs/PROJETO.md, este relatório, apresentação"]],
            [3.6, 3.6, 3.4, 5.4]),
      P("Tabela 5 — Contribuições por integrante. Fonte: git log --all.", cap)]

# 10 Próximos passos
s += [P("10. Próximos passos", h1),
      *B(["Até 19/11 (marco M4): validar conta e orçamento, provisionar com ALB, publicar a imagem com tag fixa e registrar o digest.",
          "Calibrar C no Fargate e executar A, B/C e D, com 3 repetições se possível.",
          "Validar com a Pessoa 2 a captura de logs e métricas no CloudWatch e definir o padrão dos registros.",
          "19 a 23/11: consolidar os dados, produzir os gráficos finais com unidades e metodologia e discutir os resultados.",
          "Registrar o custo real da sessão e executar a limpeza dos recursos."])]

# Referências
s += [P("Referências", h1),
      P("[1] YERRAM, S. <i>AWS EKS vs AWS ECS: A Research-Based Comparison for Container Orchestration</i>. Zenodo, 2025. "
        "Disponível em: https://zenodo.org/records/16500754.", ref),
      P("[2] AMAZON WEB SERVICES. <i>What is Amazon Elastic Container Service?</i> Disponível em: "
        "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html.", ref),
      P("[3] AMAZON WEB SERVICES. <i>Automatically scale your Amazon ECS service</i>. Disponível em: "
        "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html.", ref)]

doc.build(s)
print("ok", OUT)
