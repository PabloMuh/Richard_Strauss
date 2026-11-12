#!/usr/bin/env bash
# Verifica um endpoint (local ou ALB) e mostra a distribuição entre instâncias.
# Uso: ./scripts/smoke_test.sh http://meu-alb.amazonaws.com [N]
set -euo pipefail
BASE="${1:-http://localhost:8000}"; N="${2:-20}"
curl -fsS "$BASE/health"; echo
for _ in $(seq 1 "$N"); do
  curl -fsS "$BASE/instance" | python3 -c 'import sys,json; print(json.load(sys.stdin)["instance_id"])'
done | sort | uniq -c
