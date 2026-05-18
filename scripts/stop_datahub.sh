#!/usr/bin/env bash
# Tear DataHub down and restore the bootcamp Kafka.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v datahub >/dev/null 2>&1; then
  echo "[1/2] datahub docker quickstart --stop…"
  datahub docker quickstart --stop || true
else
  echo "[1/2] datahub CLI not found — stopping DataHub containers by name…"
  docker ps --format '{{.Names}}' | grep -E '^datahub|^elastic|^neo4j|^mysql$' | xargs -r docker stop
fi

echo "[2/2] Restarting bootcamp Kafka stack…"
docker start kafka kafka-ui de_connect

echo "Done. Bootcamp Kafka is back on 9092."
