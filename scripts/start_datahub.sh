#!/usr/bin/env bash
# Bring DataHub up alongside the bootcamp stack.
#
# DataHub ships its own Kafka on 9092, so we must stop the bootcamp Kafka first.
# Airflow / Postgres / Trino / MinIO keep running.
#
# Prereq: DataHub CLI installed in a Python 3.10/3.11 venv.
#   python3.11 -m venv .venv && source .venv/bin/activate
#   pip install "acryl-datahub[postgres,kafka]"
#
# Usage: ./scripts/start_datahub.sh [--skip-ingest]
set -euo pipefail

SKIP_INGEST=0
[[ "${1:-}" == "--skip-ingest" ]] && SKIP_INGEST=1

cd "$(dirname "$0")/.."

if ! command -v datahub >/dev/null 2>&1; then
  cat <<EOF >&2
[!] datahub CLI not on PATH. Install:
    python3.11 -m venv .venv && source .venv/bin/activate
    pip install "acryl-datahub[postgres,kafka]"
    ./scripts/start_datahub.sh
EOF
  exit 1
fi

echo "[1/4] Stopping bootcamp Kafka / Connect (port 9092 collision)…"
docker stop kafka kafka-ui de_connect >/dev/null 2>&1 || true

echo "[2/4] datahub docker quickstart…"
datahub docker quickstart

echo "[3/4] Waiting for DataHub GMS…"
until curl -fs -o /dev/null --max-time 3 http://localhost:8080/config; do
  sleep 5; printf "."
done
echo " ready."

if [[ $SKIP_INGEST -eq 0 ]]; then
  echo "[4/4] Ingest Postgres + Kafka metadata…"
  datahub ingest -c recipes/postgres.yml
  # Kafka recipe targets localhost:9092 which is DataHub's own broker after the swap.
  datahub ingest -c recipes/kafka.yml || \
    echo "[warn] Kafka ingest failed — DataHub's Kafka may still be initializing. Re-run later."
else
  echo "[4/4] Skipped ingest (--skip-ingest)."
fi

cat <<EOF

DataHub is up:
  UI   http://localhost:9002   (datahub / datahub)
  GMS  http://localhost:8080

To emit lineage from Airflow, trigger the DAG:
  docker exec -u airflow de_airflow_scheduler \\
    airflow dags trigger lab13_end_to_end_pipeline

When done, return to the bootcamp Kafka:
  ./scripts/stop_datahub.sh
EOF
