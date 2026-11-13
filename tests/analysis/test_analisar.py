"""Testes da análise com execuções sintéticas de tempos conhecidos e linhas reais do CSV do k6."""
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import analisar as a

T0 = 1_800_000_000.0  # início do k6 (epoch)
CABECALHO = ("metric_name,timestamp,metric_value,check,error,error_code,expected_response,group,method,name,proto,"
             "scenario,service,status,subproto,tls_version,url,extra_tags,metadata")
# Linhas copiadas de uma execução real do k6 1.0.0 (timeFormat=unix_milli).
LINHAS_REAIS = [
    "http_req_duration,1794530069232,639.738390,,,,true,,GET,work,HTTP/1.1,D-falha,,200,,,work,fase=constante,",
    "http_req_failed,1794530069232,0.000000,,,,true,,GET,work,HTTP/1.1,D-falha,,200,,,work,fase=constante,",
    "http_req_duration,1794530132610,2001.004200,,,1504,false,,GET,work,HTTP/1.1,D-falha,,504,,,work,fase=constante,",
    "respostas_por_instancia,1794530069232,1.000000,,,,,,,,,D-falha,,,,,,fase=constante&instancia=local-1,",
    "respostas_por_instancia,1794530132610,1.000000,,,,,,,,,D-falha,,,,,,instancia=balanceador&fase=constante,",
]


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def linha_req(t, ms, fase, ok=True, status=200, cenario="BC-escalabilidade"):
    return (f"http_req_duration,{int(t * 1000)},{ms},,,,{'true' if ok else 'false'},,GET,work,HTTP/1.1,{cenario},,{status},,,work,"
            f"fase={fase},")


def linha_inst(t, inst, fase, cenario="BC-escalabilidade"):
    return f"respostas_por_instancia,{int(t * 1000)},1,,,,,,,,,{cenario},,,,,,instancia={inst}&fase={fase},"


def criar_execucao(pasta: Path, experimento, plano, reqs, timeline, eventos, metadata_extra=None, cpu=None):
    pasta.mkdir(parents=True)
    linhas = [CABECALHO]
    for t, ms, fase, ok, inst in reqs:
        linhas.append(linha_req(t, ms, fase, ok, 200 if ok else 502, experimento))
        linhas.append(linha_inst(t, inst, fase, experimento))
    with gzip.open(pasta / "k6-bruto.csv.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    fim = max(f["fim_s"] for f in plano) if plano else 300
    (pasta / "resumo-k6.json").write_text(json.dumps({
        "cenario": experimento, "plano": plano, "inicio_utc": iso(T0), "fim_utc": iso(T0 + fim), "iteracoes_descartadas": 0}))
    (pasta / "metadata.json").write_text(json.dumps({
        "experimento": experimento, "repeticao": 1, "identificacao": {"ambiente": "aws"}, "coleta": {"intervalo_s": 10},
        **(metadata_extra or {})}))
    cab = "timestamp_utc,decorrido_s,desejadas,em_execucao,pendentes,tasks_saudaveis,alvos_saudaveis,alvos_iniciando,alvos_drenando,alvos_nao_saudaveis,tasks"
    corpo = [f"{iso(T0 + t)},{t},{d},{r},0,{s},{s},0,0,0,{tasks}" for t, d, r, s, tasks in timeline]
    (pasta / "timeline.csv").write_text("\n".join([cab] + corpo) + "\n")
    (pasta / "eventos.json").write_text(json.dumps([{"timestamp_utc": iso(T0 + t), **e} for t, e in eventos]))
    if cpu:
        (pasta / "aws").mkdir()
        (pasta / "aws" / "metricas-ecs-CPUUtilization.json").write_text(json.dumps(
            {"Datapoints": [{"Timestamp": iso(T0 + t), "Average": v, "Maximum": v + 5, "Unit": "Percent"} for t, v in cpu]}))


PLANO_BC = [  # mesmas fases do load-test.js, em segundos comprimidos; C = 2 req/s
    {"fase": "aquecimento", "inicio_s": 0, "fim_s": 60, "taxa_inicial_rps": 0.6, "taxa_final_rps": 0.6, "fracao_inicial": 0.3, "fracao_final": 0.3},
    {"fase": "subida-1", "inicio_s": 60, "fim_s": 90, "taxa_inicial_rps": 0.6, "taxa_final_rps": 1.7, "fracao_inicial": 0.3, "fracao_final": 0.85},
    {"fase": "degrau-1", "inicio_s": 90, "fim_s": 300, "taxa_inicial_rps": 1.7, "taxa_final_rps": 1.7, "fracao_inicial": 0.85, "fracao_final": 0.85},
    {"fase": "subida-2", "inicio_s": 300, "fim_s": 330, "taxa_inicial_rps": 1.7, "taxa_final_rps": 3.0, "fracao_inicial": 0.85, "fracao_final": 1.5},
    {"fase": "degrau-2", "inicio_s": 330, "fim_s": 540, "taxa_inicial_rps": 3.0, "taxa_final_rps": 3.0, "fracao_inicial": 1.5, "fracao_final": 1.5},
    {"fase": "descida", "inicio_s": 540, "fim_s": 560, "taxa_inicial_rps": 3.0, "taxa_final_rps": 0.4, "fracao_inicial": 1.5, "fracao_final": 0.2},
    {"fase": "baixa", "inicio_s": 560, "fim_s": 900, "taxa_inicial_rps": 0.4, "taxa_final_rps": 0.4, "fracao_inicial": 0.2, "fracao_final": 0.2},
]


def fase_em(t):
    return next(f["fase"] for f in PLANO_BC if f["inicio_s"] <= t < f["fim_s"])


@pytest.fixture
def execucao_bc(tmp_path):
    def latencia(s):
        if s < 260:
            return 3000.0  # 1 task a 85% de CPU
        if s < 330:
            return 600.0  # 2 tasks
        if s < 450:
            return 1500.0  # 2 tasks a 75%
        return 700.0  # 3 tasks

    reqs = [(T0 + s + 0.5, latencia(s), fase_em(s), True, "a" if s % 2 else "b") for s in range(900)]
    timeline = []
    for t in range(0, 900, 10):
        desejadas = 1 if t < 200 else 2 if t < 400 else 3 if t < 800 else 1
        saudaveis = 1 if t < 260 else 2 if t < 450 else 3 if t < 800 else 1
        timeline.append((t, desejadas, desejadas, saudaveis, ""))
    eventos = [
        (170, {"tipo": "alarme", "tipo_alarme": "alta", "estado": "ALARM", "descricao": "Alarm updated from OK to ALARM"}),
        (175, {"tipo": "escalonamento", "descricao": "Setting desired count to 2."}),
        (380, {"tipo": "alarme", "tipo_alarme": "alta", "estado": "ALARM", "descricao": "Alarm updated from OK to ALARM"}),
        (385, {"tipo": "escalonamento", "descricao": "Setting desired count to 3."}),
        (790, {"tipo": "alarme", "tipo_alarme": "baixa", "estado": "ALARM", "descricao": "Alarm updated from OK to ALARM"}),
        (795, {"tipo": "escalonamento", "descricao": "Setting desired count to 1."}),
    ]
    pasta = tmp_path / "bc"
    criar_execucao(pasta, "BC-escalabilidade", PLANO_BC, reqs, timeline, eventos,
                   {"auto_scaling": {"min": 1, "max": 3, "targetCpu": 60}}, cpu=[(0, 30.0), (60, 85.0), (120, 99.0)])
    return pasta


def test_le_linhas_reais_do_k6(tmp_path):
    arquivo = tmp_path / "real.csv.gz"
    with gzip.open(arquivo, "wt", encoding="utf-8") as f:
        f.write("\n".join([CABECALHO] + LINHAS_REAIS) + "\n")
    reqs, instancias = a.ler_k6(arquivo)
    assert len(reqs) == 2  # http_req_failed é ignorado; cada requisição conta uma vez
    assert reqs[0].t == pytest.approx(1794530069.232) and reqs[0].duracao_ms == pytest.approx(639.73839)
    assert not reqs[0].falhou and reqs[0].fase == "constante" and reqs[0].nome == "work"
    assert reqs[1].falhou and reqs[1].status == 504
    assert [i[1] for i in instancias] == ["local-1", "balanceador"]


def test_percentil_posto_mais_proximo():
    assert a.percentil([], 95) is None
    assert a.percentil(list(range(1, 101)), 95) == 95
    assert a.percentil([10, 20, 30], 50) == 20


def test_epoch_aceita_formatos_do_dotnet_e_do_cloudwatch():
    assert a.epoch("2026-11-13T00:35:22.792Z") == pytest.approx(a.epoch("2026-11-12T21:35:22.792-03:00"))
    assert a.epoch("2026-11-13T00:35:22.7921234+00:00") == pytest.approx(a.epoch("2026-11-13T00:35:22.792123Z"))


def test_escalabilidade_mede_cada_degrau(execucao_bc):
    r = a.analisar(execucao_bc)
    e = r["escalabilidade"]
    assert [(d["de"], d["para"]) for d in e["scale_out"]] == [(1, 2), (2, 3)]
    assert e["scale_out"][0]["alarme_ate_pronta_s"] == 90  # alarme 170 s -> 2 saudáveis em 260 s
    assert e["scale_out"][0]["decisao_ate_pronta_s"] == 85  # decisão 175 s
    assert e["scale_out"][1]["alarme_ate_pronta_s"] == 70  # 380 s -> 450 s
    assert e["scale_out"][1]["decisao_ate_pronta_s"] == 65
    # 1->2: carga passa de 60% de C em 60 + (0,6-0,3)/0,55*30 = 76,4 s; 2->3: passa de 120% em 300 + (1,2-0,85)/0,65*30 = 316,2 s
    assert e["scale_out"][0]["carga_acima_do_alvo_ate_pronta_s"] == pytest.approx(260 - 76.36, abs=1)
    assert e["scale_out"][1]["carga_acima_do_alvo_ate_pronta_s"] == pytest.approx(450 - 316.15, abs=1)
    assert [(d["de"], d["para"]) for d in e["scale_in"]] == [(3, 1)]
    assert e["scale_in"][0]["reducao_carga_ate_scale_in_s"] == 260  # descida em 540 s -> 800 s
    assert e["scale_in"][0]["alarme_ate_scale_in_s"] == 10
    assert e["tasks_maximo"] == 3 and e["tasks_final"] == 1


def test_mesma_carga_separada_por_tasks(execucao_bc):
    r = a.analisar(execucao_bc)
    por_fase = {g["fase"]: {n["tasks_saudaveis"]: n for n in g["grupos"]} for g in r["mesma_carga_por_tasks"]}
    assert set(por_fase) == {"aquecimento", "degrau-1", "degrau-2", "baixa"}  # só fases de carga constante
    d1, d2 = por_fase["degrau-1"], por_fase["degrau-2"]
    assert d1[1]["duracao_s"] == 170 and d1[1]["latencia_p95_ms"] == 3000.0  # 90 s -> 260 s com 1 task
    assert d1[2]["duracao_s"] == 40 and d1[2]["latencia_p95_ms"] == 600.0  # 260 s -> 300 s com 2
    assert d2[2]["duracao_s"] == 120 and d2[2]["latencia_p95_ms"] == 1500.0  # 330 s -> 450 s com 2
    assert d2[3]["duracao_s"] == 90 and d2[3]["latencia_p95_ms"] == 700.0  # 450 s -> 540 s com 3
    assert d1[1]["requisicoes"] == 170 and d1[1]["vazao_rps"] == 1.0


def test_escalabilidade_gera_relatorios_e_fases(execucao_bc):
    r = a.analisar(execucao_bc)
    assert [f["fase"] for f in r["fases"]] == ["aquecimento", "subida-1", "degrau-1", "subida-2", "degrau-2", "descida", "baixa"]
    assert r["recursos"]["cpu_maxima_pct"] == 104.0
    assert r["instancias"] == {"a": 450, "b": 450}
    resumo = (execucao_bc / "resumo.md").read_text(encoding="utf-8")
    assert "## Scale-out (B)" in resumo and "1→2" in resumo and "## Mesma carga, número de tasks diferente" in resumo
    assert json.loads((execucao_bc / "resumo.json").read_text(encoding="utf-8"))["experimento"] == "BC-escalabilidade"


def test_falha_mede_recuperacao_e_erros(tmp_path):
    plano = [{"fase": "constante", "inicio_s": 0, "fim_s": 400, "taxa_inicial_rps": 1.0, "taxa_final_rps": 1.0,
              "fracao_inicial": 0.8, "fracao_final": 0.8}]
    reqs = [(T0 + s + 0.5, 400.0 if not 180 <= s < 250 else 900.0, "constante", s not in (181, 182, 183), "x") for s in range(400)]
    timeline = []
    for t in range(0, 400, 10):
        if t < 190:
            linha = (t, 2, 2, 2, "aaa:RUNNING:HEALTHY;bbb:RUNNING:HEALTHY")
        elif t < 220:
            linha = (t, 2, 1, 1, "bbb:RUNNING:HEALTHY")
        elif t < 250:
            linha = (t, 2, 2, 1, "bbb:RUNNING:HEALTHY;ccc:PENDING:UNKNOWN")
        else:
            linha = (t, 2, 2, 2, "bbb:RUNNING:HEALTHY;ccc:RUNNING:HEALTHY")
        timeline.append(linha)
    pasta = tmp_path / "d"
    criar_execucao(pasta, "D-falha", plano, reqs, timeline, [(180, {"tipo": "stop_task", "descricao": "stop", "task": "aaa"})])
    f = a.analisar(pasta)["falha"]
    assert f["tarefa_encerrada"] == "aaa" and f["saudaveis_antes"] == 2
    assert f["tempo_ate_substituta_s"] == 40  # ccc aparece em 220 s
    assert f["tempo_recuperacao_s"] == 70  # 2 saudáveis de novo em 250 s
    assert f["erros_na_janela"] == 3
    assert f["durante"]["latencia_p95_ms"] == 900.0 and f["antes"]["latencia_p95_ms"] == 400.0


def test_sem_eventos_de_escala_nao_inventa_tempos(tmp_path):
    timeline = [(t, 1, 1, 1, "") for t in range(0, 900, 10)]
    reqs = [(T0 + s + 0.5, 1000.0, fase_em(s), True, "a") for s in range(900)]
    pasta = tmp_path / "sem-escala"
    criar_execucao(pasta, "BC-escalabilidade", PLANO_BC, reqs, timeline, [])
    e = a.analisar(pasta)["escalabilidade"]
    assert e["scale_out"] == [] and e["scale_in"] == []
    por_fase = {g["fase"]: [n["tasks_saudaveis"] for n in g["grupos"]] for g in a.analisar(pasta)["mesma_carga_por_tasks"]}
    assert por_fase["degrau-2"] == [1]
    assert "sem scale-out observado" in (pasta / "resumo.md").read_text(encoding="utf-8")


def test_consolidar_calcula_media_e_desvio(tmp_path, execucao_bc):
    raiz = execucao_bc.parent
    a.analisar(execucao_bc)
    segunda = raiz / "bc2"
    segunda.mkdir()
    for nome in ("k6-bruto.csv.gz", "resumo-k6.json", "metadata.json", "timeline.csv", "eventos.json"):
        (segunda / nome).write_bytes((execucao_bc / nome).read_bytes())
    a.analisar(segunda)
    r = a.consolidar(raiz)
    assert len(r["execucoes"]) == 2
    grupo = r["agregados"][0]
    assert grupo["experimento"] == "BC-escalabilidade" and grupo["n"] == 2
    assert grupo["scale_out_1o_degrau_s"]["media"] == 90 and grupo["scale_out_1o_degrau_s"]["desvio"] == 0
    assert grupo["scale_out_2o_degrau_s"]["media"] == 70
    linha = next(m for m in r["mesma_carga_por_tasks"] if m["fase"] == "degrau-1" and m["tasks_saudaveis"] == 1)
    assert linha["execucoes"] == 2 and linha["p95_ms"]["media"] == 3000.0
    assert (raiz / "tabela-experimental.md").exists() and (raiz / "tabela-experimental.csv").exists()


def test_graficos_sao_gerados_quando_matplotlib_existe(execucao_bc):
    pytest.importorskip("matplotlib")
    r = a.analisar(execucao_bc)
    assert set(r["graficos"]) == {"grafico-carga-latencia.png", "grafico-tasks.png", "grafico-cpu-memoria.png", "grafico-instancias.png"}
    assert all((execucao_bc / g).stat().st_size > 10_000 for g in r["graficos"])
