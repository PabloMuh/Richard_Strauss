"""Gera docs/relatorio-tecnico.pdf (Pessoa 4).

Uso, a partir da raiz do repositório:
    pip install reportlab==4.*   # ou 5.*
    python docs/gerar_pdfs.py

Fontes: Lato e DejaVu Sans Mono do sistema (pacotes fonts-lato e fonts-dejavu).
Figuras: lidas de tests/results/ (experimentos na AWS de 17/11/2026).
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
RES = RAIZ / "tests" / "results"
FIG_BC = RES / "20261117-230132-BC-escalabilidade-r1" / "grafico-tasks.png"
FIG_D = RES / "20261117-235404-D-falha-r1" / "grafico-carga-latencia.png"

L = "/usr/share/fonts/truetype/lato/"
for nome, arq in [("Lato", "Lato-Regular"), ("Lato-Bold", "Lato-Bold"), ("Lato-Italic", "Lato-Italic"),
                  ("Lato-BoldItalic", "Lato-BoldItalic"), ("Lato-Heavy", "Lato-Heavy")]:
    pdfmetrics.registerFont(TTFont(nome, f"{L}{arq}.ttf"))
pdfmetrics.registerFont(TTFont("Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
addMapping("Lato", 0, 0, "Lato"); addMapping("Lato", 1, 0, "Lato-Bold")
addMapping("Lato", 0, 1, "Lato-Italic"); addMapping("Lato", 1, 1, "Lato-BoldItalic")

NAVY = colors.HexColor("#1B3150"); TEAL = colors.HexColor("#0B7A70"); INK = colors.HexColor("#1F2A3D")
SOFT = colors.HexColor("#5A6575"); MIST = colors.HexColor("#EEF3F3"); LINE = colors.HexColor("#D5DDE0")
AMBER_BG = colors.HexColor("#FBEBDD"); AMBER = colors.HexColor("#7A3A08"); TEAL_BG = colors.HexColor("#E1F1EE")

body = ParagraphStyle("body", fontName="Lato", fontSize=10.5, leading=15, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=3, spaceAfter=3, alignment=0)
h1 = ParagraphStyle("h1", fontName="Lato-Heavy", fontSize=17, leading=22, textColor=NAVY, spaceBefore=14, spaceAfter=8)
h2 = ParagraphStyle("h2", fontName="Lato-Bold", fontSize=12.5, leading=17, textColor=TEAL, spaceBefore=10, spaceAfter=5)
cell = ParagraphStyle("cell", fontName="Lato", fontSize=9, leading=12, textColor=INK)
cellh = ParagraphStyle("cellh", parent=cell, fontName="Lato-Bold", textColor=colors.white)
cap = ParagraphStyle("cap", fontName="Lato-Italic", fontSize=9, leading=12, textColor=SOFT, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
note = ParagraphStyle("note", fontName="Lato", fontSize=9.5, leading=13.5, textColor=AMBER)
note_ok = ParagraphStyle("note_ok", parent=note, textColor=colors.HexColor("#0A5C54"))
ref = ParagraphStyle("ref", parent=body, fontSize=9.5, leading=13.5, leftIndent=14, firstLineIndent=-14, alignment=0)


def P(t, s=body): return Paragraph(t, s)
def B(items): return [Paragraph(i, bullet, bulletText="•") for i in items]
def code(t): return f'<font name="Mono" size="9">{t}</font>'


def tabela(rows, widths, zebra=True, header=True):
    data = ([[Paragraph(c, cellh) for c in rows[0]]] if header else []) + \
           [[Paragraph(c, cell) for c in r] for r in (rows[1:] if header else rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        st += [("BACKGROUND", (0, i), (-1, i), MIST) for i in range(2 if header else 1, len(data), 2)]
    t.setStyle(TableStyle(st))
    return t


def caixa(t, bg=AMBER_BG, style=note, w=16):
    x = Table([[Paragraph(t, style)]], colWidths=[w * cm])
    x.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return x


def figura(path, w, legenda):
    img = Image(str(path)); r = img.imageHeight / img.imageWidth
    img.drawWidth = w * cm; img.drawHeight = w * cm * r
    return KeepTogether([img, P(legenda, cap)])


def cabecalho(rodape):
    def desenhar(c, doc):
        c.saveState()
        c.setFont("Lato-Bold", 7.5); c.setFillColor(SOFT)
        c.drawRightString(A4[0] - 2.5 * cm, A4[1] - 1.4 * cm, "SISTEMAS DISTRIBUÍDOS  /  TEMA 7 — AMAZON ECS")
        c.setFont("Lato", 8)
        c.drawRightString(A4[0] - 2.5 * cm, 1.3 * cm, f"{rodape}   |   Página {doc.page}")
        c.restoreState()
    return desenhar


def capa(titulo2, sub1, sub2):
    def desenhar(c, doc):
        c.saveState()
        c.setFillColor(NAVY); c.rect(0, A4[1] - 11 * cm, A4[0], 11 * cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#8FD3C8")); c.setFont("Lato-Bold", 10)
        c.drawString(2.5 * cm, A4[1] - 3 * cm, "SISTEMAS DISTRIBUÍDOS  |  TEMA 7 — AMAZON ECS")
        c.setFillColor(colors.white); c.setFont("Lato-Heavy", 30)
        c.drawString(2.5 * cm, A4[1] - 5 * cm, "Orquestração de containers")
        c.drawString(2.5 * cm, A4[1] - 6.3 * cm, titulo2)
        c.setFont("Lato", 13); c.setFillColor(colors.HexColor("#BFD8D5"))
        c.drawString(2.5 * cm, A4[1] - 7.8 * cm, sub1)
        c.drawString(2.5 * cm, A4[1] - 8.5 * cm, sub2)
        c.restoreState()
    return desenhar


def documento(saida, titulo, rodape, capa_fn):
    doc = BaseDocTemplate(str(saida), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.2 * cm,
                          bottomMargin=2 * cm, title=titulo, author="Equipe Richard Strauss",
                          subject="Sistemas Distribuídos, Tema 7")
    fr = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    frc = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 10 * cm, id="c")
    doc.addPageTemplates([PageTemplate("capa", [frc], onPage=capa_fn),
                          PageTemplate("normal", [fr], onPage=cabecalho(rodape))])
    return doc


# ---------------------------------------------------------------- relatório
def relatorio():
    s = [NextPageTemplate("normal"), Spacer(1, 0.6 * cm), tabela([
        ["Disciplina", "Equipe", "Experimentos na AWS", "Data deste relatório"],
        ["Sistemas Distribuídos", "4 integrantes", "17/11/2026 · us-east-2", "25/11/2026"]], [4, 3.2, 4.4, 4.4], zebra=False),
        Spacer(1, 0.8 * cm)]
    s += [P("Resumo", h2), P(
        "Este relatório descreve o projeto do Tema 7: uma API HTTP containerizada, implantada como serviço replicado no "
        "Amazon ECS com Fargate, para observar replicação, substituição automática de tasks após falha e escalabilidade "
        "automática por uso de CPU. Os experimentos foram executados na AWS em 17/11/2026 (região us-east-2, uma repetição "
        "por cenário) e revisados contra os dados brutos em 25/11. Com 0 erros em 3 036 requisições, o serviço escalou de 1 "
        "para 3 tasks, com 35 s e 30 s entre a decisão do Auto Scaling e a nova task saudável. Voltou a 1 task em cerca de "
        "22 min e recuperou-se de uma task encerrada em 68 s, sem erro visível ao cliente. A sessão custou US$ 0,17 brutos, "
        "cobertos por créditos.")]
    s += [Spacer(1, 0.3 * cm), caixa(
        "<b>Regra de leitura.</b> Nenhum número foi estimado ou editado à mão: cada valor indica o arquivo do repositório de "
        "onde foi tirado, e os resumos são gerados por " + code("tests/analysis/analisar.py") + ". Como houve uma repetição "
        "por cenário, os tempos descrevem esta sessão e não têm média nem desvio-padrão."), PageBreak()]

    # 1
    s += [P("1. Introdução", h1), P(
        "Aplicações distribuídas precisam continuar disponíveis quando uma instância falha e acompanhar a variação de carga "
        "sem intervenção manual. Orquestradores de containers, como o Amazon Elastic Container Service (ECS), oferecem esses "
        "mecanismos de forma declarativa: o operador informa quantas cópias de uma aplicação devem existir e em que condições "
        "esse número muda, e o orquestrador mantém o estado desejado."),
        P("O objetivo da equipe foi projetar, implantar e avaliar uma aplicação HTTP containerizada no ECS, demonstrando com "
          "medições três propriedades:"),
        *B(["<b>replicação de serviço</b>: várias tasks atendem o mesmo serviço e cada resposta identifica a task que a produziu;",
            "<b>tolerância a falhas</b>: ao encerrar uma task, o ECS inicia uma substituta e o serviço volta ao número desejado;",
            "<b>escalabilidade automática</b>: o número de tasks aumenta sob carga e diminui quando ela cai."]),
        P("Banco de dados, interface web e funcionalidades de negócio ficaram fora do escopo. A pilha usada foi FastAPI, "
          "Docker, Amazon ECR, Amazon ECS com Fargate, Application Load Balancer (ALB), CloudWatch, Application Auto Scaling e k6.")]

    # 2
    s += [P("2. Fundamentação", h1),
          P("2.1 Amazon ECS e Fargate", h2), P(
        "O Amazon ECS é um serviço gerenciado de orquestração de containers. Seus conceitos centrais são o <b>cluster</b> "
        "(agrupamento lógico), a <b>task definition</b> (imagem, CPU, memória, portas, logs e health check), a <b>task</b> (uma "
        "instância em execução da task definition) e o <b>service</b>, que mantém um número desejado de tasks (<i>desired "
        "count</i>) e as registra num load balancer. Com <b>Fargate</b>, a AWS provisiona a capacidade de cada task, sem que a "
        "equipe administre instâncias EC2 [2]."),
          P("2.2 Serviço replicado e balanceamento", h2), P(
        "Replicar um serviço sem estado permite que qualquer réplica atenda qualquer requisição. Um balanceador fornece um "
        "endereço único, distribui as requisições e retira de circulação as réplicas que falham no health check. Sem ele, cada "
        "task teria um IP próprio, que muda a cada substituição."),
          P("2.3 Tolerância a falhas", h2), P(
        "O ECS service compara continuamente o número de tasks em execução com o desejado. Quando uma task para, por falha, por "
        "health check reprovado ou por encerramento manual, o agendador inicia outra. O tempo de recuperação depende do início "
        "do container e dos parâmetros dos health checks, que por isso fazem parte da configuração registrada."),
          P("2.4 Escalabilidade automática", h2), P(
        "O Application Auto Scaling ajusta o desired count de um service. Na política de <b>target tracking</b>, define-se um "
        "valor-alvo para uma métrica, aqui a CPU média do serviço, e o serviço cria alarmes no CloudWatch que disparam o aumento "
        "ou a redução de tasks [3]. Os cooldowns limitam a frequência das mudanças, e a redução é mais conservadora que o "
        "aumento, para evitar oscilação."),
          P("2.5 Trade-offs", h2),
          *B(["<b>Custo × disponibilidade</b>: mais tasks e um ALB aumentam disponibilidade e capacidade, mas cobram por hora.",
              "<b>Reatividade × estabilidade</b>: alvos baixos e avaliações curtas reagem mais rápido, mas podem oscilar.",
              "<b>Simplicidade × controle</b>: Fargate dispensa gerenciar servidores, mas limita tamanhos de task e acesso ao host.",
              "<b>ECS × EKS</b>: o ECS é integrado à AWS e mais simples de operar; o EKS oferece portabilidade e um ecossistema "
              "maior, com mais complexidade operacional [1]."])]

    # 3
    s += [P("3. Arquitetura e implementação", h1), P(
        "O Quadro 1 resume a arquitetura efetivamente usada em 17/11 (" + code("docs/fechamento-infraestrutura.md") + ")."),
          tabela([["Componente", "Configuração"],
                  ["Conta e região", "us-east-2 (Ohio), única região liberada pela política (SCP) da conta experimental"],
                  ["Gerador de carga", "k6 1.0.0 em Docker numa máquina local, alcançando o ALB pela internet"],
                  ["Entrada", "ALB HTTP:80 → target group de IPs na porta 8000; health check /health a cada 10 s, limiares 2, drenagem de 30 s"],
                  ["ECS service", "richard-strauss-api, Fargate, Linux x86_64, awsvpc, 0,25 vCPU e 512 MiB; VPC padrão, duas zonas"],
                  ["Imagem", "richard-strauss:api-62f1e8e, task definition rev. 3, fixada no digest"],
                  ["Observabilidade", "CloudWatch Logs /ecs/richard-strauss (7 dias); métricas AWS/ECS e AWS/ApplicationELB"],
                  ["Auto Scaling", "Target tracking da CPU média; alvo 60%; 1 a 3 tasks; cooldown 60 s (aumento) e 180 s (redução)"]],
                 [3.4, 12.6]),
          P("Quadro 1 — Arquitetura implantada em 17/11/2026. Fonte: docs/fechamento-infraestrutura.md.", cap),
          P("3.1 Aplicação", h2), P(
        "A API foi escrita em Python 3.12 com FastAPI e Uvicorn (" + code("app/") + "). É stateless e expõe três rotas JSON; "
        "toda resposta traz os headers " + code("x-instance-id") + " e " + code("x-request-id") + "."),
          tabela([["Rota", "Comportamento", "Papel nos experimentos"],
                  ["GET /health", "Retorna {\"status\":\"ok\"}; assíncrona, responde no event loop", "Health check do container e do ALB"],
                  ["GET /instance", "ID da task (metadados ECS v4), versão, zona, uptime", "Distinguir réplicas"],
                  ["GET /work", "200 000 hashes SHA-256 encadeados por padrão; ~0,55 s no Fargate (~2,7 ms por 1 000 iterações)",
                   "Carga de CPU controlada"]], [3.0, 8.0, 5.0]),
          Spacer(1, 6), P(
        "A imagem parte de " + code("python:3.12-slim") + ", roda como usuário não-root e é construída para " + code("linux/amd64") +
        ". A configuração é feita só por variáveis de ambiente, sem segredos, e os logs saem em JSON, uma linha por requisição. "
        "Há 12 testes automatizados (pytest) e um workflow de CI. Pelo ALB, 30 consultas a " + code("/instance") + " foram "
        "divididas igualmente entre as duas tasks (15 e 15)."),
          P("3.2 Infraestrutura", h2), P(
        "A infraestrutura é descrita por scripts PowerShell 7 e modelos JSON versionados (" + code("infrastructure/") + "), usando "
        "a AWS CLI v2: verificação do ambiente, provisionamento de ECR, cluster, security groups e ALB, publicação da imagem, "
        "implantação, Auto Scaling, consulta, teste HTTP e limpeza."),
          *B(["Os scripts exigem conta conferida, orçamento e janela registrados antes de criar recursos.",
              "Cada recurso recebe tags de propriedade e entra num inventário; a limpeza só remove o que comprovadamente foi criado.",
              "As tasks só aceitam tráfego do security group do ALB; não há NAT Gateway e credenciais não são versionadas.",
              "35 casos de teste offline rodam no GitHub Actions sem acesso à AWS."]),
          P("3.3 Ferramentas de medição", h2), P(
        "O script k6 (" + code("tests/load-test.js") + ") gera os cenários; o orquestrador " + code("Invoke-Experiment.ps1") +
        " confere pré-condições, roda o k6, amostra o estado do ECS e do ALB a cada 10 s, executa o " + code("stop-task") +
        " em D e exporta métricas, eventos e alarmes; a análise " + code("analisar.py") + " produz resumos, gráficos e a tabela "
        "experimental. Todo o fluxo foi validado antes num ambiente Docker local, sem AWS.")]

    # 4
    s += [P("4. Problemas encontrados e corrigidos", h1),
          P("4.1 /health sob carga (API-02, validação local)", h2), P(
        "Com 0,25 vCPU, vários cálculos de " + code("/work") + " em paralelo disputavam a GIL do Python e atrasavam o " +
        code("/health") + ". Sob carga, o ECS consideraria a task doente e a substituiria no meio dos experimentos."),
          tabela([["Situação (docker --cpus 0.25)", "Falhas de /health (timeout 5 s)", "/health p50 / p95", "Vazão de /work"],
                  ["Antes: 20 clientes, 60 s", "85%", "—", "—"],
                  ["Depois: 20 clientes, 90 s", "0 de 90", "86 / 186 ms", "1,81 req/s"],
                  ["Depois: 60 clientes, 60 s", "0 de 60", "78 / 173 ms", "1,80 req/s"]], [5.4, 4.0, 3.3, 3.3]),
          P("Tabela 1 — Efeito da correção do API-02. Fonte: docs/validacao-local.md.", cap), P(
        "A correção tornou " + code("/health") + " assíncrono e passou a executar " + code("/work") + " numa thread, com no máximo "
        "um cálculo por vez (" + code("WORK_CONCURRENCY") + "); os demais pedidos esperam na fila sem consumir CPU."),
          P("4.2 HTTP 502 do ALB por keep-alive (AWS)", h2), P(
        "A primeira execução do baseline na AWS teve 1 erro em 225 requisições (0,44%): um 502 gerado pelo ALB em 156 ms, sem "
        "registro da requisição nos logs da API. O Uvicorn fechava conexões ociosas após 5 s, enquanto o ALB as reutiliza por "
        "até 60 s. O keep-alive passou a 75 s (commit " + code("62f1e8e") + "). Com a imagem corrigida, A, B/C e D somaram 3 036 "
        "requisições sem erro e sem 5XX no ALB. A execução antiga está em " + code("tests/results/pre-correcao/") + " e fica fora "
        "da tabela consolidada.")]

    # 5
    s += [P("5. Metodologia", h1), P(
        "Como " + code("/work") + " é limitado por CPU e cada task processa um cálculo por vez, a unidade de carga é <b>C</b>, a "
        "vazão máxima de uma task, medida na calibração do mesmo dia: <b>C = 1,50 req/s</b> no Fargate (CPU a 100%). Com carga L "
        "e N tasks, a CPU média é aproximadamente L / (N·C), e o target tracking busca N ≈ L / (0,6·C)."),
          tabela([["Experimento", "Tasks", "Carga planejada", "Hipótese"],
                  ["A · Baseline", "1, sem Auto Scaling", "0,5 C por 5 min", "Vazão ≈ oferecida, erros < 1%, CPU entre 35% e 65%"],
                  ["B · Scale-out", "1 → 3", "0,3 C; degraus de 0,85 C (6 min) e 1,5 C (7 min)", "1→2→3 tasks; p95 menor com mais tasks na mesma carga"],
                  ["C · Scale-in", "3 → 1", "0,2 C por 22 min + 5 min", "Retorno a 1 task, erros < 1%"],
                  ["D · Falha", "2, sem Auto Scaling", "0,8 C por 10 min; stop-task aos 3 min", "Substituta saudável no ALB; erros na janela < 1%"]],
                 [2.8, 2.8, 4.8, 5.6]),
          P("Tabela 2 — Desenho experimental. Fonte: tests/plano-de-testes.md.", cap),
          *B(["<b>Scale-out</b>: da decisão do Auto Scaling até a nova task saudável no ALB, por degrau; também a reação completa, "
              "da carga passar do alvo até a task pronta;",
              "<b>Scale-in</b>: do início da redução de carga até cada decisão de redução;",
              "<b>Recuperação</b>: do pedido de stop-task até o ALB voltar ao número anterior de alvos saudáveis."]),
          P("O estado do serviço foi amostrado a cada 10 s, e as métricas do CloudWatch têm períodos de 1 min. O k6 cumpriu o "
            "plano cerca de 4% mais devagar que o relógio, e a análise corrige os instantes derivados do plano por esse fator.")]

    # 6
    s += [P("6. Resultados na AWS", h1),
          tabela([["Experimento", "Requisições", "Erros", "p50 / p95 (ms)", "CPU média", "Resultado principal"],
                  ["Calibração", "283", "0%", "2 487 / 3 829", "100%", "C = 1,50 req/s por task"],
                  ["A · Baseline", "225", "0%", "660 / 1 014", "48,7%", "1 task a ~0,48 C, vazão 0,72 req/s"],
                  ["B/C · Escalabilidade", "2 091", "0%", "692 / 1 301", "32,4%", "1→2→3 e 3→2→1 tasks"],
                  ["D · Falha", "720", "0%", "690 / 1 106", "39,8%", "Recuperação em 68 s"]], [3.3, 2.1, 1.4, 2.6, 1.9, 4.7]),
          P("Tabela 3 — Resultados consolidados, uma repetição por cenário. Fonte: tests/results/RESUMO-AWS-20261117.md e "
            "tabela-experimental.md.", cap),
          KeepTogether([P("6.1 Scale-out (B)", h2),
          tabela([["Degrau", "Carga acima do alvo", "Alarme", "Decisão", "Task saudável", "Decisão → pronta", "Carga → pronta"],
                  ["1 → 2", "23:04:12", "23:10:50", "23:10:50", "23:11:25", "35 s", "433 s"],
                  ["2 → 3", "23:11:30", "(continuou em ALARM)", "23:13:50", "23:14:21", "30 s", "171 s"]],
                 [1.5, 2.6, 2.9, 1.9, 2.3, 2.4, 2.4]),
          P("Tabela 4 — Linha do tempo do scale-out, horários UTC. Fonte: BC-escalabilidade-r1/conclusao.md.", cap)]), P(
        "O ECS levou de 30 a 35 s da decisão até a task saudável no ALB. A reação completa do primeiro degrau, 433 s, é dominada "
        "pela cadeia de métricas: o alarme exige 3 datapoints de 1 min acima de 60% e mudou de estado quase 3 min depois do "
        "terceiro. O segundo degrau aproveitou o alarme, que continuava em ALARM, e esperou só o cooldown de 60 s."),
          figura(FIG_BC, 16, "Figura 1 — Tasks desejadas, em execução e saudáveis ao longo do experimento B/C (amostra a cada "
                 "10 s). Fonte: tests/results/20261117-230132-BC-escalabilidade-r1/grafico-tasks.png."),
          P("6.2 Scale-in (C)", h2), P(
        "A carga caiu às 23:19:17. O alarme de baixa exige 15 datapoints abaixo de 54% e foi para ALARM às 23:31:45; a contagem "
        "começou ainda no degrau de carga alta, porque com 3 tasks a CPU já estava entre 48% e 52%. A primeira redução (3→2) "
        "saiu 1 108 s após a queda da carga e a segunda (2→1), após o cooldown de 180 s, aos 1 348 s: cerca de 22 min para "
        "voltar a 1 task, uma de cada vez, embora a CPU média da fase baixa tenha ficado em 9,6%. A hipótese de cerca de 15 min "
        "se confirmou só em parte."),
          P("6.3 Mesma carga, número de tasks diferente", h2),
          tabela([["Fase (carga planejada)", "Tasks saudáveis", "Requisições", "p50 (ms)", "p95 (ms)", "&gt; 1 s"],
                  ["degrau-1 (0,85 C)", "1", "442", "700", "1 476", "13,1%"],
                  ["degrau-2 (1,5 C)", "2", "353", "728", "1 392", "9,6%"],
                  ["degrau-2 (1,5 C)", "3", "550", "679", "1 074", "6,0%"],
                  ["baixa (0,2 C)", "1", "24", "674", "724", "4,2%"],
                  ["baixa (0,2 C)", "2", "68", "684", "751", "1,5%"],
                  ["baixa (0,2 C)", "3", "345", "690", "1 163", "6,4%"]], [4.0, 2.4, 2.4, 2.2, 2.2, 2.8]),
          P("Tabela 5 — Latência sob a mesma carga planejada. Fonte: tests/results/tabela-experimental.md.", cap), P(
        "Com carga alta, passar de 2 para 3 tasks reduziu o p50 em 7% e o p95 em 23%, com a mesma vazão e sem erros. Com carga "
        "baixa, o p50 ficou praticamente igual com 1, 2 ou 3 tasks: mais tasks só melhoram a latência quando cada task está "
        "carregada. O p95 maior com 3 tasks na carga baixa vem da cauda periódica (seção 7), não do número de tasks."),
          KeepTogether([P("6.4 Falha (D)", h2),
          tabela([["Instante", "Evento"],
                  ["+0 s", "Pedido de stop-task para uma das 2 tasks"],
                  ["+35,7 s", "Última resposta da task parada: ela continuou atendendo enquanto o ECS reagia"],
                  ["+36,5 s / +37 s", "O ECS tira o alvo do ALB, inicia a drenagem e cria a substituta"],
                  ["+68 s", "Substituta saudável no ALB: recuperação completa"],
                  ["+97 s", "O container parado encerra com código 0, após a drenagem de 30 s"]], [3.2, 12.8]),
          P("Tabela 6 — Linha do tempo da falha. Fonte: D-falha-r1/conclusao.md.", cap)]), P(
        "Não houve erros nas 119 requisições da janela da falha nem nas 720 da execução. A parada é ordenada (o ECS tira o alvo "
        "do ALB e drena as conexões antes de encerrar o container), e a task restante tinha folga, com cerca de 0,77 C. A "
        "capacidade ficou reduzida por cerca de 31 s; nesse intervalo, o p95 subiu de 1 082 para 1 710 ms, sem fila crescente."),
          figura(FIG_D, 14.5, "Figura 2 — Experimento D: vazão, carga oferecida e latência (baldes de 10 s); a linha preta marca o "
                 "stop-task. Fonte: tests/results/20261117-235404-D-falha-r1/grafico-carga-latencia.png.")]

    # 7
    s += [P("7. Discussão e limitações", h1),
          *B(["<b>O ECS é rápido; a cadeia de métricas, não.</b> Criar e registrar uma task leva cerca de meio minuto, tanto no "
              "scale-out quanto na substituição (31 s em D). O tempo de reação ao aumento de carga é dominado pela avaliação dos "
              "alarmes; reduzi-lo exigiria outra política, como step scaling com menos períodos de avaliação.",
              "<b>Redução conservadora.</b> O scale-in levou cerca de 22 min, mantendo tasks ociosas e custo maior, em troca de "
              "estabilidade.",
              "<b>Mais tasks não provam desempenho.</b> A latência só caiu com mais tasks sob carga alta, na mesma carga oferecida.",
              "<b>Cauda de latência periódica.</b> Em todas as tasks, de 4% a 10% das requisições passaram de 1 s, e de 49% a 80% "
              "delas começam na mesma faixa de 5 s de um ciclo de 30 s, o intervalo do health check do container. É a causa "
              "provável, não testada isoladamente.",
              "<b>Uma repetição por cenário</b>, contra três preferidas no plano: sem média nem desvio-padrão.",
              "<b>Gerador numa máquina doméstica:</b> a latência inclui a rede até us-east-2, e a carga efetiva foi ~96% da planejada.",
              "<b>Falha controlada:</b> só stop-task com drenagem; uma queda abrupta seria detectada pelo health check e pode gerar erros.",
              "<b>Imagem:</b> smoke e calibração usaram a versão anterior à correção do keep-alive, que não altera o custo de CPU."])]

    # 8
    s += [P("8. Custos e limpeza", h1),
          tabela([["Componente (Cost Explorer, 16 a 24/11)", "Custo bruto (US$)"],
                  ["Elastic Load Balancing", "0,0676"], ["ECS / Fargate", "0,0528"], ["VPC (IPv4 público)", "0,0470"],
                  ["ECR (armazenamento)", "0,0012"], ["<b>Total bruto</b> (créditos aplicados: −0,17; líquido: 0,00)", "<b>0,1686</b>"]],
                 [11, 5]),
          P("Tabela 7 — Custo da sessão experimental. Fonte: docs/inventario-custos-20261124.md.", cap), P(
        "A cobrança de ECS, ELB e VPC ocorreu só em 17 e 18/11; o saldo do Free Plan ficou em US$ 99,83 de 100. O primeiro deploy, "
        "de 12/11 em outra conta, tem custo estimado de US$ 0,10. Na consulta de 24/11, cluster, serviço, tasks, ALB, alvos do Auto "
        "Scaling, IPv4 públicos e security groups do projeto não existiam mais; foram mantidos o repositório ECR (duas imagens), o "
        "grupo de logs com retenção de 7 dias e a role de execução, criada manualmente.")]

    # 9
    s += [P("9. Contribuições da equipe", h1), P(
        "A divisão segue o plano da equipe e foi conferida no histórico Git de todas as branches (" + code("git log --all") + ")."),
          tabela([["Integrante", "Responsabilidade", "Principais entregas"],
                  ["Pessoa 1 (LandriAlencars)", "Aplicação, Docker e imagem",
                   "API, Dockerfile e testes; implantação e execução dos experimentos na AWS em 17/11; correção do keep-alive; "
                   "inventário final e custos (24/11); seção da aplicação"],
                  ["Pessoa 2 (PabloMuh)", "Infraestrutura AWS e implantação",
                   "Scripts e modelos de infraestrutura; primeiro deploy (12/11); revisão dos eventos do ECS e do Auto Scaling; "
                   "fechamento da infraestrutura e dos custos"],
                  ["Pessoa 3 (leonardo-lbp)", "Auto Scaling, carga e testes",
                   "Correções de integração (health check, API-02); Auto Scaling; k6, orquestrador e análise; revisão dos resultados "
                   "da AWS e correção da medição do 2º degrau (25/11)"],
                  ["Pessoa 4 (Matheus)", "Observabilidade e documentação",
                   "Visão geral do projeto, relatório técnico e apresentação"]], [3.6, 3.6, 8.8]),
          P("Tabela 8 — Contribuições por integrante. Fonte: git log --all.", cap), P(
        "O primeiro resumo dos resultados da AWS foi gerado com ferramenta de IA durante a execução (commit " + code("629f0a7") +
        ") e revisado pela Pessoa 3 contra os dados brutos; a revisão corrigiu o tempo do 2º degrau de 210 s para 30 s e a CPU "
        "do baseline de 37,7% para 48,7%.")]

    # 10
    s += [P("10. Conclusão", h1), P(
        "As três propriedades foram observadas com dados reais. As réplicas dividiram a carga pelo ALB; uma task encerrada foi "
        "reposta em 68 s sem erro visível ao cliente; e o serviço escalou de 1 para 3 tasks e voltou a 1, com latência menor sob "
        "carga alta. O ECS age em cerca de meio minuto; o que domina o tempo de reação é a configuração dos alarmes e dos cooldowns. "
        "Como trabalho futuro ficam as repetições 2 e 3 de cada cenário, um teste de queda abrupta e uma política de escala mais "
        "reativa.")]

    s += [P("Referências", h1),
          P("[1] YERRAM, S. <i>AWS EKS vs AWS ECS: A Research-Based Comparison for Container Orchestration</i>. Zenodo, 2025. "
            "Disponível em: https://zenodo.org/records/16500754.", ref),
          P("[2] AMAZON WEB SERVICES. <i>What is Amazon Elastic Container Service?</i> Disponível em: "
            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html.", ref),
          P("[3] AMAZON WEB SERVICES. <i>Automatically scale your Amazon ECS service</i>. Disponível em: "
            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html.", ref)]

    doc = documento(DOCS / "relatorio-tecnico.pdf", "Relatório técnico — Orquestração de containers com Amazon ECS",
                    "Relatório técnico • 25/11/2026",
                    capa("com Amazon ECS", "Relatório técnico: arquitetura, implementação, método e",
                         "resultados dos experimentos na AWS"))
    doc.build(s)



if __name__ == "__main__":

    relatorio()

    print("ok:", DOCS / "relatorio-tecnico.pdf")
