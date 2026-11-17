"""Análise dos experimentos da pessoa 3.

Uso:
    python tests/analysis/analisar.py analisar <pasta-do-experimento>
    python tests/analysis/analisar.py consolidar <pasta-de-resultados>

`analisar` lê o que tests/scripts/Invoke-Experiment.ps1 grava (metadata.json, resumo-k6.json,
k6-bruto.csv.gz, timeline.csv, eventos.json e aws/*.json) e produz resumo.json, resumo.md e
gráficos brutos em PNG (se o matplotlib estiver instalado).

`consolidar` junta os resumo.json de várias execuções numa tabela experimental, com média e
desvio-padrão por experimento e a comparação entre uma e várias tasks.

Nenhum número é estimado ou preenchido: indicadores sem dados aparecem como null / "—".
"""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl

BALDE_S = 10  # resolução das séries temporais (s)
ALVO_CPU_PADRAO = 60.0


@dataclass
class Requisicao:
    t: float  # fim da requisição, epoch em segundos
    duracao_ms: float
    falhou: bool
    status: int
    fase: str
    nome: str


# ----------------------------------------------------------------------------- leitura

def epoch(valor) -> float | None:
    """Converte ISO 8601 (com Z, offset ou fração longa do .NET) em epoch UTC."""
    if valor in (None, ""):
        return None
    texto = str(valor).strip().replace("Z", "+00:00")
    texto = re.sub(r"(\.\d{6})\d+", r"\1", texto)
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.timestamp()


def ler_json(caminho: Path, padrao=None):
    if not caminho.exists():
        return padrao
    with caminho.open(encoding="utf-8-sig") as arquivo:
        return json.load(arquivo)


def ler_k6(caminho: Path) -> tuple[list[Requisicao], list[tuple[float, str, str]]]:
    """Lê o CSV do k6 (gz ou texto). Devolve as requisições HTTP e as respostas por instância."""
    if not caminho.exists():
        return [], []
    abrir = gzip.open if caminho.suffix == ".gz" else open
    requisicoes: list[Requisicao] = []
    instancias: list[tuple[float, str, str]] = []
    with abrir(caminho, "rt", encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            nome_metrica = linha["metric_name"]
            if nome_metrica not in ("http_req_duration", "respostas_por_instancia"):
                continue
            bruto = float(linha["timestamp"])
            t = bruto / 1000 if bruto > 1e11 else bruto  # unix_milli ou unix (s)
            extras = dict(parse_qsl(linha.get("extra_tags") or ""))
            if nome_metrica == "http_req_duration":
                status = int(float(linha["status"] or 0))
                requisicoes.append(Requisicao(
                    t=t,
                    duracao_ms=float(linha["metric_value"]),
                    falhou=(linha.get("expected_response") or "").lower() != "true",
                    status=status,
                    fase=extras.get("fase", ""),
                    nome=linha.get("name") or "",
                ))
            else:
                instancias.append((t, extras.get("instancia", "?"), extras.get("fase", "")))
    requisicoes.sort(key=lambda r: r.t)
    instancias.sort()
    return requisicoes, instancias


def ler_timeline(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    linhas = []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            item = {"t": epoch(linha["timestamp_utc"]), "tasks": linha.get("tasks", "")}
            for chave in ("desejadas", "em_execucao", "pendentes", "tasks_saudaveis", "alvos_saudaveis",
                          "alvos_iniciando", "alvos_drenando", "alvos_nao_saudaveis"):
                valor = linha.get(chave, "")
                item[chave] = int(float(valor)) if valor not in ("", None) else None
            item["saudaveis"] = item["alvos_saudaveis"] if item["alvos_saudaveis"] is not None else item["tasks_saudaveis"]
            linhas.append(item)
    return sorted(linhas, key=lambda x: x["t"])


def ler_metrica(caminho: Path) -> list[dict]:
    dados = ler_json(caminho, {}) or {}
    pontos = []
    for ponto in dados.get("Datapoints", []):
        item = {"t": epoch(ponto["Timestamp"])}
        for chave, valor in ponto.items():
            if chave not in ("Timestamp", "Unit"):
                item[chave] = valor
        if "ExtendedStatistics" in ponto:
            item.update(ponto["ExtendedStatistics"])
        pontos.append(item)
    return sorted(pontos, key=lambda p: p["t"])


# ----------------------------------------------------------------------------- estatística

def percentil(valores: list[float], p: float) -> float | None:
    """Percentil pelo método do posto mais próximo (sem interpolação)."""
    if not valores:
        return None
    ordenados = sorted(valores)
    posto = max(1, math.ceil(p / 100 * len(ordenados)))
    return ordenados[posto - 1]


def arred(valor, casas=2):
    return None if valor is None else round(valor, casas)


def estatisticas(reqs: list[Requisicao], duracao_s: float | None) -> dict:
    duracoes = [r.duracao_ms for r in reqs if not r.falhou]
    erros = sum(1 for r in reqs if r.falhou)
    return {
        "requisicoes": len(reqs),
        "erros": erros,
        "taxa_erros_pct": arred(100 * erros / len(reqs), 3) if reqs else None,
        "vazao_rps": arred(sum(1 for r in reqs if not r.falhou) / duracao_s, 3) if duracao_s else None,
        "latencia_p50_ms": arred(percentil(duracoes, 50), 1),
        "latencia_p95_ms": arred(percentil(duracoes, 95), 1),
        "latencia_p99_ms": arred(percentil(duracoes, 99), 1),
        "latencia_max_ms": arred(max(duracoes), 1) if duracoes else None,
    }


def series(reqs: list[Requisicao], inicio: float, fim: float, balde: int = BALDE_S) -> list[dict]:
    if fim <= inicio:
        return []
    grupos: dict[int, list[Requisicao]] = defaultdict(list)
    for r in reqs:
        grupos[int((r.t - inicio) // balde)].append(r)
    resultado = []
    for i in range(int(math.ceil((fim - inicio) / balde))):
        grupo = grupos.get(i, [])
        ok = [r.duracao_ms for r in grupo if not r.falhou]
        resultado.append({
            "t_s": i * balde, "vazao_rps": len(ok) / balde, "erros": sum(1 for r in grupo if r.falhou),
            "p50_ms": percentil(ok, 50), "p95_ms": percentil(ok, 95),
        })
    return resultado


# ----------------------------------------------------------------------------- indicadores

def primeira(linhas: list[dict], condicao, depois: float = -math.inf) -> dict | None:
    return next((l for l in linhas if l["t"] >= depois and condicao(l)), None)


def eventos_do_tipo(eventos: list[dict], tipo: str, **filtros) -> list[dict]:
    selecionados = []
    for e in eventos:
        if e.get("tipo") != tipo:
            continue
        if all(str(e.get(k, "")).upper() == str(v).upper() for k, v in filtros.items()):
            selecionados.append({**e, "t": epoch(e["timestamp_utc"])})
    return sorted(selecionados, key=lambda e: e["t"])


def mudancas_desejadas(timeline: list[dict]) -> list[dict]:
    mudancas = []
    for anterior, atual in zip(timeline, timeline[1:]):
        if anterior["desejadas"] is not None and atual["desejadas"] is not None and atual["desejadas"] != anterior["desejadas"]:
            mudancas.append({"t": atual["t"], "de": anterior["desejadas"], "para": atual["desejadas"]})
    return mudancas


def momento_taxa(plano: list[dict], fracao_alvo: float, inicio: float) -> float | None:
    """Primeiro instante em que a taxa oferecida (fração da capacidade de 1 task) atinge fracao_alvo."""
    for fase in plano:
        de, ate = fase["fracao_inicial"], fase["fracao_final"]
        if de >= fracao_alvo:
            return inicio + fase["inicio_s"]
        if de < fracao_alvo <= ate:
            return inicio + fase["inicio_s"] + (fracao_alvo - de) / (ate - de) * (fase["fim_s"] - fase["inicio_s"])
    return None


def mesma_carga_por_tasks(plano, reqs, timeline, inicio) -> list[dict]:
    """Em cada fase de carga constante, separa as requisições pelo número de tasks saudáveis no momento."""
    if not timeline:
        return []
    tempos = [l["t"] for l in timeline]
    resultado = []
    for fase in plano:
        if fase["fracao_inicial"] != fase["fracao_final"]:
            continue
        ini, fim = inicio + fase["inicio_s"], inicio + fase["fim_s"]
        duracao: dict[int, float] = defaultdict(float)
        for i, linha in enumerate(timeline):
            a = max(linha["t"], ini)
            b = min(timeline[i + 1]["t"] if i + 1 < len(timeline) else fim, fim)
            if b > a and linha["saudaveis"] is not None:
                duracao[linha["saudaveis"]] += b - a
        grupos: dict[int, list[Requisicao]] = defaultdict(list)
        for r in reqs:
            if r.fase == fase["fase"] and ini <= r.t < fim:
                k = bisect.bisect_right(tempos, r.t) - 1
                if k >= 0 and timeline[k]["saudaveis"] is not None:
                    grupos[timeline[k]["saudaveis"]].append(r)
        resultado.append({
            "fase": fase["fase"], "carga_oferecida_rps": arred(fase["taxa_final_rps"], 3),
            "grupos": [{"tasks_saudaveis": n, "duracao_s": arred(duracao[n], 1), **estatisticas(grupos[n], duracao[n] or None)}
                       for n in sorted(set(duracao) | set(grupos))],
        })
    return resultado


def indicadores_escala(timeline, eventos, plano, inicio, reqs, alvo_cpu, intervalo_coleta) -> dict:
    mudancas = mudancas_desejadas(timeline)
    alarmes_alta = eventos_do_tipo(eventos, "alarme", tipo_alarme="alta", estado="ALARM")
    alarmes_baixa = eventos_do_tipo(eventos, "alarme", tipo_alarme="baixa", estado="ALARM")
    escalonamentos = eventos_do_tipo(eventos, "escalonamento")
    t_carga = momento_taxa(plano, alvo_cpu / 100, inicio)
    fase_inicio = {f["fase"]: inicio + f["inicio_s"] for f in plano}
    t_reducao = fase_inicio.get("descida", fase_inicio.get("baixa"))

    degraus_out, degraus_in = [], []
    for m in mudancas:
        antes = [a for a in (alarmes_alta if m["para"] > m["de"] else alarmes_baixa) if a["t"] <= m["t"]]
        alarme = antes[-1]["t"] if antes else None
        atividade = next((e["t"] for e in escalonamentos if e["t"] <= m["t"] and (alarme is None or e["t"] >= alarme)), None)
        if m["para"] > m["de"]:
            pronta = primeira(timeline, lambda l, alvo=m["para"]: (l["saudaveis"] or 0) >= alvo, depois=m["t"])
            # Carga que leva as tasks existentes acima da CPU-alvo: alvo × tasks antes do degrau (frações de C).
            t_carga_degrau = momento_taxa(plano, alvo_cpu / 100 * m["de"], inicio)
            degraus_out.append({
                "de": m["de"], "para": m["para"],
                "carga_acima_do_alvo_utc": iso(t_carga_degrau),
                "alarme_utc": iso(alarme), "decisao_utc": iso(atividade), "desejadas_observadas_utc": iso(m["t"]),
                "task_pronta_utc": iso(pronta["t"]) if pronta else None,
                "alarme_ate_pronta_s": arred(pronta["t"] - alarme, 0) if pronta and alarme else None,
                "decisao_ate_pronta_s": arred(pronta["t"] - (atividade or m["t"]), 0) if pronta else None,
                "carga_acima_do_alvo_ate_pronta_s": arred(pronta["t"] - t_carga_degrau, 0) if pronta and t_carga_degrau else None,
            })
        else:
            degraus_in.append({
                "de": m["de"], "para": m["para"],
                "alarme_utc": iso(alarme), "decisao_utc": iso(atividade), "desejadas_observadas_utc": iso(m["t"]),
                "reducao_carga_ate_scale_in_s": arred(m["t"] - t_reducao, 0) if t_reducao else None,
                "alarme_ate_scale_in_s": arred(m["t"] - alarme, 0) if alarme else None,
            })

    return {
        "carga_acima_do_alvo_utc": iso(t_carga),
        "reducao_da_carga_utc": iso(t_reducao),
        "scale_out": degraus_out,
        "scale_in": degraus_in,
        "tasks_maximo": max((l["desejadas"] or 0) for l in timeline) if timeline else None,
        "tasks_final": timeline[-1]["desejadas"] if timeline else None,
        "resolucao_s": intervalo_coleta,
    }


def indicadores_falha(timeline, eventos, reqs, intervalo_coleta) -> dict:
    paradas = eventos_do_tipo(eventos, "stop_task")
    if not paradas:
        return {"observacao": "nenhum evento stop_task registrado"}
    t_stop = paradas[0]["t"]
    antes = [l for l in timeline if l["t"] < t_stop]
    n_antes = antes[-1]["saudaveis"] if antes else None
    ids_antes = {p.split(":")[0] for p in (antes[-1]["tasks"].split(";") if antes else []) if p}
    queda = primeira(timeline, lambda l: n_antes is not None and (l["saudaveis"] or 0) < n_antes, depois=t_stop)
    recuperada = primeira(timeline, lambda l: n_antes is not None and (l["saudaveis"] or 0) >= n_antes, depois=queda["t"]) if queda else None
    nova = primeira(timeline, lambda l: any(p.split(":")[0] not in ids_antes for p in l["tasks"].split(";") if p), depois=t_stop)
    reposicoes = eventos_do_tipo(eventos, "start_replica")
    t_nova = nova["t"] if nova else (reposicoes[0]["t"] if reposicoes else None)
    fim_janela = (recuperada["t"] if recuperada else (reqs[-1].t if reqs else t_stop)) + 30
    janela = [r for r in reqs if t_stop - 5 <= r.t <= fim_janela]
    return {
        "parada_utc": iso(t_stop),
        "tarefa_encerrada": paradas[0].get("task"),
        "saudaveis_antes": n_antes,
        "queda_observada_utc": iso(queda["t"]) if queda else None,
        "substituta_vista_utc": iso(t_nova),
        "recuperada_utc": iso(recuperada["t"]) if recuperada else None,
        "tempo_ate_substituta_s": arred(t_nova - t_stop, 0) if t_nova else None,
        "tempo_recuperacao_s": arred(recuperada["t"] - t_stop, 0) if recuperada else None,
        "erros_na_janela": sum(1 for r in janela if r.falhou),
        "requisicoes_na_janela": len(janela),
        "antes": estatisticas([r for r in reqs if t_stop - 60 <= r.t < t_stop], 60),
        "durante": estatisticas([r for r in reqs if recuperada and t_stop <= r.t < recuperada["t"]], (recuperada["t"] - t_stop) if recuperada else None),
        "depois": estatisticas([r for r in reqs if recuperada and r.t >= recuperada["t"] + 30],
                               (reqs[-1].t - recuperada["t"] - 30) if recuperada and reqs and reqs[-1].t > recuperada["t"] + 30 else None),
        "resolucao_s": intervalo_coleta,
    }


def iso(t: float | None) -> str | None:
    return None if t is None else datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def janela_cloudwatch(pontos: list[dict], inicio: float, fim: float, chave: str) -> list[float]:
    # Datapoints de 1 min marcados pelo início do período: inclui os que cobrem a janela do k6.
    return [p[chave] for p in pontos if chave in p and inicio - 60 < p["t"] < fim]


def analisar(pasta: Path) -> dict:
    metadata = ler_json(pasta / "metadata.json", {}) or {}
    resumo_k6 = ler_json(pasta / "resumo-k6.json", {}) or {}
    eventos = ler_json(pasta / "eventos.json", []) or []
    reqs, instancias = ler_k6(next((p for p in (pasta / "k6-bruto.csv.gz", pasta / "k6-bruto.csv") if p.exists()), pasta / "k6-bruto.csv.gz"))
    timeline = ler_timeline(pasta / "timeline.csv")
    plano = resumo_k6.get("plano") or []
    experimento = metadata.get("experimento") or resumo_k6.get("cenario") or pasta.name
    trabalho = [r for r in reqs if r.nome == "work"] or reqs

    inicio = epoch(resumo_k6.get("inicio_utc")) or (trabalho[0].t if trabalho else None)
    fim = epoch(resumo_k6.get("fim_utc")) or (trabalho[-1].t if trabalho else None)
    duracao = (fim - inicio) if inicio and fim else None

    resultado: dict = {
        "pasta": pasta.name,
        "experimento": experimento,
        "repeticao": metadata.get("repeticao"),
        "ambiente": (metadata.get("identificacao") or {}).get("ambiente"),
        "inicio_utc": iso(inicio), "fim_utc": iso(fim), "duracao_s": arred(duracao, 1),
        "k6": {k: resumo_k6.get(k) for k in ("capacidade_rps", "iteracoes", "escala_tempo", "iteracoes_descartadas", "vus_max", "taxa_checks", "capacidade_estimada_rps")},
        "geral": estatisticas(trabalho, duracao),
        "fases": [],
        "instancias": dict(Counter(i for _, i, _ in instancias)),
    }
    for fase in plano:
        da_fase = [r for r in trabalho if r.fase == fase["fase"]]
        dur = fase["fim_s"] - fase["inicio_s"]
        resultado["fases"].append({
            "fase": fase["fase"], "duracao_s": dur,
            "carga_oferecida_rps": arred((fase["taxa_inicial_rps"] + fase["taxa_final_rps"]) / 2, 3),
            **estatisticas(da_fase, dur),
            "instancias": dict(Counter(i for _, i, f in instancias if f == fase["fase"])),
        })

    cpu = ler_metrica(pasta / "aws" / "metricas-ecs-CPUUtilization.json")
    memoria = ler_metrica(pasta / "aws" / "metricas-ecs-MemoryUtilization.json")
    if inicio and fim and (cpu or memoria):
        media_cpu = janela_cloudwatch(cpu, inicio, fim, "Average")
        max_cpu = janela_cloudwatch(cpu, inicio, fim, "Maximum")
        media_mem = janela_cloudwatch(memoria, inicio, fim, "Average")
        resultado["recursos"] = {
            "cpu_media_pct": arred(statistics.fmean(media_cpu), 1) if media_cpu else None,
            "cpu_maxima_pct": arred(max(max_cpu), 1) if max_cpu else None,
            "memoria_media_pct": arred(statistics.fmean(media_mem), 1) if media_mem else None,
            "observacao": "média dos datapoints de 1 min do serviço (média entre as tasks)",
        }

    intervalo = (metadata.get("coleta") or {}).get("intervalo_s")
    alvo_cpu = float((metadata.get("auto_scaling") or {}).get("targetCpu") or ALVO_CPU_PADRAO)
    if inicio and timeline and plano:
        resultado["mesma_carga_por_tasks"] = mesma_carga_por_tasks(plano, trabalho, timeline, inicio)
    if experimento == "BC-escalabilidade" and inicio:
        resultado["escalabilidade"] = indicadores_escala(timeline, eventos, plano, inicio, trabalho, alvo_cpu, intervalo)
    if experimento == "D-falha":
        resultado["falha"] = indicadores_falha(timeline, eventos, trabalho, intervalo)
    if experimento == "calibracao" and inicio and trabalho:
        estavel = [r for r in trabalho if r.t >= inicio + 20 and not r.falhou]
        resultado["calibracao"] = {
            "capacidade_estimada_rps": arred(resumo_k6.get("capacidade_estimada_rps"), 3),
            "vazao_estavel_rps": arred(len(estavel) / (fim - inicio - 20), 3) if fim and fim - inicio > 20 else None,
            "observacao": "use vazao_estavel_rps (exclui os 20 s iniciais) como CAPACIDADE_RPS",
        }

    (pasta / "resumo.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    (pasta / "resumo.md").write_text(resumo_markdown(resultado, metadata, eventos), encoding="utf-8")
    graficos = gerar_graficos(pasta, trabalho, instancias, timeline, eventos, plano, cpu, memoria, inicio, fim, alvo_cpu, metadata)
    resultado["graficos"] = graficos
    return resultado


# ----------------------------------------------------------------------------- saída

def fmt(valor, sufixo="") -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        valor = f"{valor:.3f}".rstrip("0").rstrip(".")
    return f"{valor}{sufixo}"


def tabela(cabecalho: list[str], linhas: list[list]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(fmt(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(saida)


def resumo_markdown(r: dict, metadata: dict, eventos: list[dict]) -> str:
    ident = metadata.get("identificacao") or {}
    k6 = metadata.get("k6") or {}
    partes = [
        f"# Resumo — {r['experimento']} (repetição {fmt(r['repeticao'])})",
        "",
        "Gerado por `tests/analysis/analisar.py` a partir dos arquivos desta pasta. Interpretação em `conclusao.md`.",
        "",
        "## Identificação e configuração",
        "",
        tabela(["Campo", "Valor"], [
            ["Objetivo", metadata.get("objetivo")], ["Responsável", metadata.get("responsavel")],
            ["Ambiente", ident.get("ambiente")], ["Região", ident.get("regiao")],
            ["Imagem", (ident.get("imagem") or {}).get("tag") if isinstance(ident.get("imagem"), dict) else None],
            ["Task definition", ident.get("task_definition")],
            ["Início / fim (UTC)", f"{fmt(r['inicio_utc'])} / {fmt(r['fim_utc'])}"],
            ["Capacidade de 1 task usada (req/s)", k6.get("capacidade_rps")], ["Iterações por /work", k6.get("iteracoes") or "padrão do servidor"],
            ["Escala de tempo", k6.get("escala_tempo")], ["Auto Scaling", json.dumps(metadata.get("auto_scaling"), ensure_ascii=False) if metadata.get("auto_scaling") else "desativado"],
            ["Coleta do estado (s)", (metadata.get("coleta") or {}).get("intervalo_s")],
        ]),
        "",
        "## Resultado geral (k6)",
        "",
        tabela(["Requisições", "Erros (%)", "Vazão (req/s)", "p50 (ms)", "p95 (ms)", "p99 (ms)", "Iterações descartadas"], [[
            r["geral"]["requisicoes"], r["geral"]["taxa_erros_pct"], r["geral"]["vazao_rps"], r["geral"]["latencia_p50_ms"],
            r["geral"]["latencia_p95_ms"], r["geral"]["latencia_p99_ms"], r["k6"].get("iteracoes_descartadas")]]),
    ]
    if r["fases"]:
        partes += ["", "## Por fase", "", tabela(
            ["Fase", "Duração (s)", "Oferecida (req/s)", "Vazão (req/s)", "Erros (%)", "p50 (ms)", "p95 (ms)", "Respostas por instância"],
            [[f["fase"], f["duracao_s"], f["carga_oferecida_rps"], f["vazao_rps"], f["taxa_erros_pct"], f["latencia_p50_ms"], f["latencia_p95_ms"],
              ", ".join(f"{k}: {v}" for k, v in sorted(f["instancias"].items()))] for f in r["fases"]])]
    if r.get("recursos"):
        rec = r["recursos"]
        partes += ["", "## CPU e memória (CloudWatch)", "", tabela(["CPU média (%)", "CPU máxima (%)", "Memória média (%)"],
                                                                 [[rec["cpu_media_pct"], rec["cpu_maxima_pct"], rec["memoria_media_pct"]]]), "", rec["observacao"] + "."]
    if r.get("escalabilidade"):
        e = r["escalabilidade"]
        partes += ["", "## Scale-out (B)", "",
                   f"Máximo de tasks: {fmt(e['tasks_maximo'])}; final: {fmt(e['tasks_final'])}. \"Carga acima do alvo\" é o momento em que a carga oferecida "
                   "passa da CPU-alvo para as tasks existentes antes do degrau.", "",
                   tabela(["Degrau", "Carga acima do alvo", "Alarme", "Decisão", "Task pronta", "Alarme→pronta (s)", "Decisão→pronta (s)", "Carga→pronta (s)"],
                          [[f"{d['de']}→{d['para']}", d["carga_acima_do_alvo_utc"], d["alarme_utc"], d["decisao_utc"], d["task_pronta_utc"], d["alarme_ate_pronta_s"],
                            d["decisao_ate_pronta_s"], d["carga_acima_do_alvo_ate_pronta_s"]] for d in e["scale_out"]] or [["sem scale-out observado"] + [None] * 7]),
                   "", "## Scale-in (C)", "", f"Carga reduzida em {fmt(e['reducao_da_carga_utc'])}.", "",
                   tabela(["Degrau", "Alarme", "Decisão", "Desejadas reduzidas", "Redução da carga→scale-in (s)", "Alarme→scale-in (s)"],
                          [[f"{d['de']}→{d['para']}", d["alarme_utc"], d["decisao_utc"], d["desejadas_observadas_utc"], d["reducao_carga_ate_scale_in_s"],
                            d["alarme_ate_scale_in_s"]] for d in e["scale_in"]] or [["sem scale-in observado"] + [None] * 5])]
        partes += ["", f"Tempos medidos a partir do estado amostrado a cada {fmt(e['resolucao_s'])} s (resolução da medição)."]
    if r.get("mesma_carga_por_tasks"):
        linhas = [[g["fase"], g["carga_oferecida_rps"], n["tasks_saudaveis"], n["duracao_s"], n["requisicoes"], n["vazao_rps"], n["taxa_erros_pct"],
                   n["latencia_p50_ms"], n["latencia_p95_ms"]] for g in r["mesma_carga_por_tasks"] for n in g["grupos"]]
        partes += ["", "## Mesma carga, número de tasks diferente", "",
                   "Em cada fase de carga constante, as requisições são separadas pelo número de tasks saudáveis no momento em que terminaram. "
                   "É a comparação entre uma e várias tasks sob a mesma carga oferecida.", "",
                   tabela(["Fase", "Oferecida (req/s)", "Tasks saudáveis", "Tempo (s)", "Requisições", "Vazão (req/s)", "Erros (%)", "p50 (ms)", "p95 (ms)"], linhas)]
    if r.get("falha"):
        f = r["falha"]
        if "parada_utc" in f:
            partes += ["", "## Falha (D)", "", tabela(["Indicador", "Valor"], [
                ["Task encerrada", f["tarefa_encerrada"]], ["Parada", f["parada_utc"]], ["Queda observada", f["queda_observada_utc"]],
                ["Substituta vista", f["substituta_vista_utc"]], ["Recuperada (saudáveis como antes)", f["recuperada_utc"]],
                ["Tempo até a substituta (s)", f["tempo_ate_substituta_s"]], ["Tempo de recuperação (s)", f["tempo_recuperacao_s"]],
                ["Erros na janela da falha", f"{f['erros_na_janela']} de {f['requisicoes_na_janela']}"]]),
                "", tabela(["Período", "Vazão (req/s)", "Erros (%)", "p50 (ms)", "p95 (ms)"],
                           [[nome, f[k]["vazao_rps"], f[k]["taxa_erros_pct"], f[k]["latencia_p50_ms"], f[k]["latencia_p95_ms"]]
                            for nome, k in (("60 s antes", "antes"), ("durante", "durante"), ("depois (+30 s)", "depois"))]),
                "", f"Tempos medidos a partir do estado amostrado a cada {fmt(f['resolucao_s'])} s."]
        else:
            partes += ["", "## Falha (D)", "", f["observacao"]]
    if r.get("calibracao"):
        c = r["calibracao"]
        partes += ["", "## Calibração", "", tabela(["Capacidade estimada pelo k6 (req/s)", "Vazão estável (req/s)"],
                                                 [[c["capacidade_estimada_rps"], c["vazao_estavel_rps"]]]), "", c["observacao"] + "."]
    if eventos:
        partes += ["", "## Linha do tempo", "", tabela(["UTC", "Tipo", "Descrição"],
                                                     [[e.get("timestamp_utc"), e.get("tipo"), (e.get("descricao") or "").replace("|", "/")] for e in eventos])]
    return "\n".join(partes) + "\n"


def gerar_graficos(pasta, reqs, instancias, timeline, eventos, plano, cpu, memoria, inicio, fim, alvo_cpu, metadata) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib ausente: gráficos não gerados (pip install -r tests/requirements.txt)", file=sys.stderr)
        return []
    if not inicio or not fim:
        return []
    gerados = []
    rel = lambda t: (t - inicio) / 60  # minutos desde o início do k6
    titulo = f"{metadata.get('experimento', '')} r{metadata.get('repeticao', '')}"
    marcas = []
    for e in eventos:
        t = epoch(e.get("timestamp_utc"))
        if t is None:
            continue
        if e.get("tipo") == "alarme" and str(e.get("estado", "")).upper() == "ALARM":
            marcas.append((t, "tab:red" if e.get("tipo_alarme") == "alta" else "tab:blue", "--"))
        elif e.get("tipo") == "stop_task":
            marcas.append((t, "black", "-"))
        elif e.get("tipo") in ("escalonamento", "start_replica"):
            marcas.append((t, "tab:green", ":"))

    def decorar(eixo):
        for f in plano:
            eixo.axvspan(f["inicio_s"] / 60, f["fim_s"] / 60, alpha=0.06 if plano.index(f) % 2 else 0.0, color="gray")
        for t, cor, estilo in marcas:
            eixo.axvline(rel(t), color=cor, linestyle=estilo, linewidth=1)
        eixo.grid(alpha=0.3)

    serie = series(reqs, inicio, fim)
    if serie:
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        x = [(s["t_s"] + BALDE_S / 2) / 60 for s in serie]  # cada balde no ponto médio do intervalo
        a1.plot(x, [s["vazao_rps"] for s in serie], label="vazão (req/s, OK)")
        if plano:
            xs, ys = [], []
            for f in plano:
                xs += [f["inicio_s"] / 60, f["fim_s"] / 60]
                ys += [f["taxa_inicial_rps"], f["taxa_final_rps"]]
            a1.plot(xs, ys, "k--", linewidth=1, label="carga oferecida (req/s)")
        erros = [s["erros"] / BALDE_S for s in serie]
        if any(erros):
            a1.bar(x, erros, width=BALDE_S / 60, color="tab:red", alpha=0.6, label="erros (req/s)")
        a1.set_ylabel("req/s")
        a1.legend(loc="upper right", fontsize=8)
        a1.set_title(f"{titulo}: vazão, carga e latência (baldes de {BALDE_S} s)")
        decorar(a1)
        a2.plot(x, [s["p50_ms"] / 1000 if s["p50_ms"] is not None else None for s in serie], label="p50")
        a2.plot(x, [s["p95_ms"] / 1000 if s["p95_ms"] is not None else None for s in serie], label="p95")
        a2.set_ylabel("latência (s)")
        a2.set_xlabel("minutos desde o início do k6")
        a2.legend(loc="upper right", fontsize=8)
        decorar(a2)
        for f in plano:
            a2.annotate(f["fase"], (f["inicio_s"] / 60, 1), xycoords=("data", "axes fraction"), fontsize=7, va="top")
        fig.tight_layout()
        fig.savefig(pasta / "grafico-carga-latencia.png", dpi=110)
        plt.close(fig)
        gerados.append("grafico-carga-latencia.png")

    if timeline:
        fig, eixo = plt.subplots(figsize=(11, 3.8))
        x = [rel(l["t"]) for l in timeline]
        eixo.step(x, [l["desejadas"] for l in timeline], where="post", label="desejadas")
        eixo.step(x, [l["em_execucao"] for l in timeline], where="post", label="em execução")
        eixo.step(x, [l["saudaveis"] for l in timeline], where="post", label="saudáveis (alvos do ALB ou health check)", linestyle="--")
        eixo.set_ylabel("tasks")
        eixo.set_xlabel("minutos desde o início do k6")
        eixo.set_title(f"{titulo}: tasks ao longo do tempo (amostra a cada {(metadata.get('coleta') or {}).get('intervalo_s', '?')} s)")
        eixo.yaxis.get_major_locator().set_params(integer=True)
        eixo.legend(loc="upper right", fontsize=8)
        decorar(eixo)
        fig.tight_layout()
        fig.savefig(pasta / "grafico-tasks.png", dpi=110)
        plt.close(fig)
        gerados.append("grafico-tasks.png")

    if cpu or memoria:
        fig, eixo = plt.subplots(figsize=(11, 3.8))
        if cpu:
            eixo.plot([rel(p["t"]) for p in cpu], [p.get("Average") for p in cpu], marker="o", label="CPU média do serviço (%)")
            eixo.plot([rel(p["t"]) for p in cpu], [p.get("Maximum") for p in cpu], marker=".", linestyle=":", label="CPU máxima (%)")
        if memoria:
            eixo.plot([rel(p["t"]) for p in memoria], [p.get("Average") for p in memoria], label="memória média (%)")
        if metadata.get("auto_scaling"):
            eixo.axhline(alvo_cpu, color="tab:red", linewidth=1, linestyle="--", label=f"alvo do Auto Scaling ({alvo_cpu:g}%)")
        eixo.set_ylim(0, 105)
        eixo.set_ylabel("%")
        eixo.set_xlabel("minutos desde o início do k6 (datapoints de 1 min do CloudWatch)")
        eixo.set_title(f"{titulo}: CPU e memória")
        eixo.legend(loc="upper right", fontsize=8)
        decorar(eixo)
        fig.tight_layout()
        fig.savefig(pasta / "grafico-cpu-memoria.png", dpi=110)
        plt.close(fig)
        gerados.append("grafico-cpu-memoria.png")

    if instancias:
        balde = 30
        nomes = sorted({i for _, i, _ in instancias})
        n = int(math.ceil((fim - inicio) / balde)) or 1
        contagens = {nome: [0] * n for nome in nomes}
        for t, nome, _ in instancias:
            i = int((t - inicio) // balde)
            if 0 <= i < n:
                contagens[nome][i] += 1
        fig, eixo = plt.subplots(figsize=(11, 3.8))
        eixo.stackplot([(i + 0.5) * balde / 60 for i in range(n)], [[c / balde for c in contagens[nome]] for nome in nomes],
                       labels=[nome[:12] for nome in nomes], alpha=0.8)
        eixo.set_ylabel("respostas/s")
        eixo.set_xlabel("minutos desde o início do k6")
        eixo.set_title(f"{titulo}: respostas por instância (baldes de {balde} s)")
        eixo.legend(loc="upper right", fontsize=7, ncol=2)
        decorar(eixo)
        fig.tight_layout()
        fig.savefig(pasta / "grafico-instancias.png", dpi=110)
        plt.close(fig)
        gerados.append("grafico-instancias.png")
    return gerados


# ----------------------------------------------------------------------------- consolidação

INDICADORES = [
    ("vazao_rps", lambda r: r["geral"]["vazao_rps"]),
    ("p95_ms", lambda r: r["geral"]["latencia_p95_ms"]),
    ("erros_pct", lambda r: r["geral"]["taxa_erros_pct"]),
    ("cpu_media_pct", lambda r: (r.get("recursos") or {}).get("cpu_media_pct")),
    ("tasks_max", lambda r: (r.get("escalabilidade") or {}).get("tasks_maximo")),
    ("scale_out_1o_degrau_s", lambda r: next((d["alarme_ate_pronta_s"] for d in (r.get("escalabilidade") or {}).get("scale_out", [])), None)),
    ("scale_in_s", lambda r: next((d["reducao_carga_ate_scale_in_s"] for d in (r.get("escalabilidade") or {}).get("scale_in", [])), None)),
    ("scale_out_2o_degrau_s", lambda r: next((d["alarme_ate_pronta_s"] for d in (r.get("escalabilidade") or {}).get("scale_out", [])[1:]), None)),
    ("recuperacao_s", lambda r: (r.get("falha") or {}).get("tempo_recuperacao_s")),
    ("erros_falha", lambda r: (r.get("falha") or {}).get("erros_na_janela")),
]


def media_desvio(valores: list) -> dict:
    valores = [v for v in valores if v is not None]
    return {"media": arred(statistics.fmean(valores), 2) if valores else None,
            "desvio": arred(statistics.stdev(valores), 2) if len(valores) > 1 else None, "n": len(valores)}


def fmt_md(d: dict) -> str | None:
    return f"{fmt(d['media'])} ± {fmt(d['desvio'])} (n={d['n']})" if d["media"] is not None else None


def consolidar(raiz: Path) -> dict:
    execucoes = []
    por_tasks = defaultdict(list)
    for resumo in sorted(raiz.glob("*/resumo.json")):
        r = ler_json(resumo)
        execucoes.append({"pasta": r["pasta"], "experimento": r["experimento"], "ambiente": r.get("ambiente"), "repeticao": r.get("repeticao"),
                          "inicio_utc": r.get("inicio_utc"), **{nome: f(r) for nome, f in INDICADORES}})
        for g in r.get("mesma_carga_por_tasks") or []:
            for n in g["grupos"]:
                por_tasks[(r["experimento"], r.get("ambiente"), g["fase"], g["carga_oferecida_rps"], n["tasks_saudaveis"])].append(n)
    grupos = defaultdict(list)
    for e in execucoes:
        grupos[(e["experimento"], e["ambiente"])].append(e)
    agregados = []
    for (experimento, ambiente), itens in sorted(grupos.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        linha = {"experimento": experimento, "ambiente": ambiente, "n": len(itens)}
        for nome, _ in INDICADORES:
            linha[nome] = media_desvio([i[nome] for i in itens])
        agregados.append(linha)
    mesma_carga = [{"experimento": k[0], "ambiente": k[1], "fase": k[2], "carga_oferecida_rps": k[3], "tasks_saudaveis": k[4], "execucoes": len(v),
                    "vazao_rps": media_desvio([x["vazao_rps"] for x in v]), "p95_ms": media_desvio([x["latencia_p95_ms"] for x in v]),
                    "erros_pct": media_desvio([x["taxa_erros_pct"] for x in v])}
                   for k, v in sorted(por_tasks.items(), key=lambda kv: tuple(str(x) for x in kv[0]))]
    resultado = {"execucoes": execucoes, "agregados": agregados, "mesma_carga_por_tasks": mesma_carga}
    (raiz / "tabela-experimental.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    with (raiz / "tabela-experimental.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(execucoes[0].keys()) if execucoes else ["pasta"])
        escritor.writeheader()
        escritor.writerows(execucoes)
    nomes = [n for n, _ in INDICADORES]
    md = ["# Tabela experimental", "", "Gerada por `tests/analysis/analisar.py consolidar`. Média ± desvio-padrão (n = execuções com o indicador).", "",
          tabela(["Experimento", "Ambiente", "Execuções"] + nomes,
                 [[a["experimento"], a["ambiente"], a["n"]] + [fmt_md(a[n]) for n in nomes] for a in agregados]),
          "", "## Mesma carga, número de tasks diferente", "",
          "Requisições de cada fase de carga constante separadas pelo número de tasks saudáveis no momento (média entre execuções).", "",
          tabela(["Experimento", "Ambiente", "Fase", "Oferecida (req/s)", "Tasks saudáveis", "Execuções", "Vazão (req/s)", "p95 (ms)", "Erros (%)"],
                 [[m["experimento"], m["ambiente"], m["fase"], m["carga_oferecida_rps"], m["tasks_saudaveis"], m["execucoes"],
                   fmt_md(m["vazao_rps"]), fmt_md(m["p95_ms"]), fmt_md(m["erros_pct"])] for m in mesma_carga]),
          "", "## Execuções", "",
          tabela(["Pasta", "Experimento", "Rep."] + nomes, [[e["pasta"], e["experimento"], e["repeticao"]] + [e[n] for n in nomes] for e in execucoes])]
    (raiz / "tabela-experimental.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return resultado


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("analisar").add_argument("pasta", type=Path)
    sub.add_parser("consolidar").add_argument("raiz", type=Path)
    args = parser.parse_args(argv)
    if args.comando == "analisar":
        r = analisar(args.pasta)
        print(f"Análise de {args.pasta.name}: {r['geral']['requisicoes']} requisições, erros {fmt(r['geral']['taxa_erros_pct'], '%')}, "
              f"p95 {fmt(r['geral']['latencia_p95_ms'], ' ms')}. Arquivos: resumo.md, resumo.json, {', '.join(r['graficos']) or 'sem gráficos'}.")
    else:
        r = consolidar(args.raiz)
        print(f"Consolidadas {len(r['execucoes'])} execuções em {args.raiz / 'tabela-experimental.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
