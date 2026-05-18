# Demo cheat sheet — Lakehouse Stack

## Live demo dashboard

There's a **live mock control-plane UI** at [`demo/dashboard.html`](demo/dashboard.html).
It polls every service every 5 s and shows a real pipeline graph, status pills, and
counts pulled out of the running containers.

```bash
./scripts/demo_serve.py            # serves the dashboard + status proxy on :7777
open http://localhost:7777
```

Screenshots (auto-rendered from the live page):

- Pipeline diagram: [`demo/screenshots/dashboard_pipeline.png`](demo/screenshots/dashboard_pipeline.png)
- Full dashboard:  [`demo/screenshots/dashboard_full.png`](demo/screenshots/dashboard_full.png)
- Wide overview:   [`demo/screenshots/dashboard_overview.png`](demo/screenshots/dashboard_overview.png)

A slide deck for the demo lives at [`demo/lakehouse_demo.pptx`](demo/lakehouse_demo.pptx).

---

Stack state captured **2026-05-13**. Two ports differ from the README:

| Service          | Documented | Actual (this host) | Why                           |
|------------------|------------|--------------------|-------------------------------|
| Trino UI         | 8081       | **8181**           | host port 8081 was occupied   |
| Metabase UI      | 3000       | **3001**           | host port 3000 was occupied   |

All other ports match the README.

---

## 1. Sanity check (run first, ~5 s)

```bash
for u in \
  "trino     http://localhost:8181/v1/info" \
  "minio     http://localhost:9001" \
  "airflow   http://localhost:8085/health" \
  "connect   http://localhost:8083/connectors" \
  "kafka-ui  http://localhost:8082" \
  "metabase  http://localhost:3001/api/health"; do
  name=$(echo $u | awk '{print $1}'); url=$(echo $u | awk '{print $2}')
  printf "%-10s %s\n" "$name" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 $url)"
done
```

Every line should print `200`.

---

## 2. Demo flow (≈ 15 min talk track)

### Act 1 — Postgres as the OLTP source (Lab 3 / 6)

```bash
docker exec -it de_postgres psql -U de_user -d de_db
```

```sql
\dt bootcamp_dw.*
SELECT * FROM bootcamp_dw.mart_daily_category_sales;     -- 3 rows
SELECT * FROM orders;                                    -- 5 rows from orders.csv
```

Talking point: classical star schema, SCD types 1/2/6 are encoded in `dim_customers`.

### Act 2 — Lakehouse over MinIO via Trino (Lab 7)

```bash
docker exec -it trino trino
```

```sql
SHOW CATALOGS;                                           -- lakehouse, postgres, system
SHOW SCHEMAS IN lakehouse;                               -- bronze, silver, gold
SELECT * FROM lakehouse.bronze.orders_raw;               -- 3 rows, includes "bad_amount"
SELECT * FROM lakehouse.silver.orders_clean;             -- 2 rows, cast + filtered
SELECT * FROM lakehouse.gold.customer_sales;             -- 1 row aggregate

-- Cross-engine join: lakehouse gold ∪ operational orders
SELECT 'gold' AS src, customer_id::VARCHAR AS k, total_revenue::VARCHAR AS v
FROM   lakehouse.gold.customer_sales
UNION ALL
SELECT 'pg',   order_id::VARCHAR,  (quantity*unit_price)::VARCHAR
FROM   postgres.public.orders;
```

Open http://localhost:9001 (login `minio` / `minio12345`) → `lakehouse` bucket → show `bronze/`, `silver/`, `gold/` parquet/text files.

### Act 3 — Streaming (Lab 10 + Kafka UI)

Topic `orders` is preloaded with 3 JSON events.

```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic orders \
  --from-beginning --max-messages 3 --timeout-ms 4000
```

UI: http://localhost:8082 → Topics → `orders` → Messages.

### Act 4 — Orchestration (Lab 13)

http://localhost:8085 — login `airflow` / `airflow`.
DAG **`lab13_end_to_end_pipeline`** is unpaused.
Trigger it from the UI (▶) — 5 tasks (sensor → validate → bronze → silver → gold) finish in seconds with green status.

### Act 5 — BI (Lab 6)

http://localhost:3001 — Metabase. First-run will ask for an admin account; afterwards add the Postgres source:

- Host `de_postgres` (or `host.docker.internal:5432`)
- DB `de_db`, user `de_user`, password `de_password`

Then build a question on `bootcamp_dw.mart_daily_category_sales`.

### Act 6 — Governance & lineage with DataHub (Lab 15)

DataHub is **not** part of the always-on stack — it has its own Kafka and would
collide on 9092. One command does the swap:

```bash
./scripts/start_datahub.sh
```

What that script does:
1. Stops `kafka`, `kafka-ui`, `de_connect` (frees port 9092).
2. Runs `datahub docker quickstart` — pulls the upstream DataHub stack (GMS, ES,
   Neo4j, MySQL, front-end).
3. Ingests metadata from `recipes/postgres.yml` and `recipes/kafka.yml`.

Prerequisite: install the DataHub CLI in a Python 3.10/3.11 venv (the README
warns 3.13 is unsupported):

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install "acryl-datahub[postgres,kafka]"
```

Then in the demo:

- DataHub UI → http://localhost:9002 (`datahub` / `datahub`)
- **Datasets → postgres → de_db** — see `public.orders`, `lab06_dw.*`, `bootcamp_dw.*` cataloged with column-level schema.
- **Trigger the DAG again** so the Airflow DataHub plugin emits run-time lineage:
  ```bash
  docker exec -u airflow de_airflow_scheduler \
    airflow dags trigger lab13_end_to_end_pipeline
  ```
- **Pipelines → Airflow → lab13_end_to_end_pipeline → Lineage** — shows
  Postgres → bronze → silver → gold edges from `inlets`/`outlets`.
- Enrich a dataset with **owner / tag / glossary term** to demonstrate governance UX.

When done, restore the bootcamp Kafka so the rest of the labs work:

```bash
./scripts/stop_datahub.sh
```

---

## 3. Reset between demos

```bash
# Re-seed Postgres lab data
docker exec -i de_postgres psql -U de_user -d de_db < lab03_setup.sql
docker exec -i de_postgres psql -U de_user -d de_db < lab06_setup.sql

# Re-seed lakehouse
docker exec trino trino --execute "$(cat lab07_setup.sql)"

# Re-seed Kafka topic
docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --delete --topic orders 2>/dev/null
docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic orders --partitions 3 --replication-factor 1
docker exec kafka sh -c 'printf "%s\n" \
  "{\"order_id\":1,\"product\":\"Notebook\",\"qty\":2,\"amount\":31.0}" \
  "{\"order_id\":2,\"product\":\"Pen Set\",\"qty\":1,\"amount\":20.0}" \
  "{\"order_id\":3,\"product\":\"Desk Lamp\",\"qty\":3,\"amount\":36.0}" \
  | kafka-console-producer --bootstrap-server localhost:9092 --topic orders'
```

---

## 4. Quick troubleshooting

| Symptom                                      | Action                                                                 |
|----------------------------------------------|------------------------------------------------------------------------|
| `Trino server is still initializing`         | Wait ~30 s after `docker restart trino`                                |
| `port 8081 / 3000 already in use`            | These have been remapped to **8181 / 3001** in `docker-compose.yml`    |
| Airflow CLI exits with `No module 'airflow'` | Run as `docker exec -u airflow de_airflow_scheduler airflow …`         |
| Metabase returns 502 right after restart     | First boot does H2 migration; give it ~60 s                            |
| DataHub demo wanted                          | Stop bootcamp Kafka first (`docker stop kafka`), it collides on 9092   |
