#!/usr/bin/env bash
# Evidência de 05/11: build da imagem e duas instâncias locais respondendo.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=docs/evidencias
mkdir -p "$OUT"

docker build --build-arg APP_VERSION=local -t ecs-api:local .
docker rm -f api-1 api-2 >/dev/null 2>&1 || true
docker run -d --name api-1 -p 8081:8000 -e INSTANCE_ID=api-1 ecs-api:local
docker run -d --name api-2 -p 8082:8000 -e INSTANCE_ID=api-2 ecs-api:local

for i in $(seq 1 20); do
  curl -fs localhost:8081/health >/dev/null && curl -fs localhost:8082/health >/dev/null && break
  sleep 0.5
done

{
  echo "# $(date -Iseconds)"; docker ps --filter name=api- --format '{{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
  for p in 8081 8082; do
    echo; echo "## porta $p"
    echo "\$ curl localhost:$p/health";   curl -s localhost:$p/health; echo
    echo "\$ curl localhost:$p/instance"; curl -s localhost:$p/instance; echo
    echo "\$ curl 'localhost:$p/work?iterations=100000'"; curl -s "localhost:$p/work?iterations=100000"; echo
  done
} | tee "$OUT/duas-instancias.txt"

echo; echo "Evidência salva em $OUT/duas-instancias.txt (pare com: docker rm -f api-1 api-2)"
