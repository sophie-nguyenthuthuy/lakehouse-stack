# Lab 15 — Data Governance & Metadata (DataHub)

## Objectives
- Hiểu governance vs management; 3 nhóm metadata (technical / business / operational).
- Ingest metadata từ Postgres, Kafka, Airflow vào DataHub.
- Xem lineage và enrich asset bằng owner / tags / glossary.

## Prerequisites
DataHub CLI:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "acryl-datahub[postgres,kafka,airflow]"
```

DataHub stack (không nằm trong `docker-compose.yml` chính; dùng quickstart của DataHub):
```bash
datahub docker quickstart
```
DataHub UI sẽ chạy tại `http://localhost:9002` (default).

## Bước 1 — Start DataHub + các nguồn
```bash
docker compose up -d postgres kafka zookeeper airflow-webserver airflow-scheduler
datahub docker quickstart
```

## Bước 2 — Review 3 recipes
File sẵn có:
- [`recipes/postgres.yml`](../recipes/postgres.yml) — source `postgres`, ingest tables từ `de_db`.
- [`recipes/kafka.yml`](../recipes/kafka.yml) — source `kafka`, ingest topics.
- [`recipes/airflow.yml`](../recipes/airflow.yml) — source `airflow`, ingest DAGs/tasks.

Ví dụ Postgres recipe:
```yaml
source:
  type: postgres
  config:
    host_port: localhost:5432
    database: de_db
    username: de_user
    password: de_password
sink:
  type: datahub-rest
  config:
    server: http://localhost:8080
```

## Bước 3 — Ingest
```bash
datahub ingest -c recipes/postgres.yml
datahub ingest -c recipes/kafka.yml
datahub ingest -c recipes/airflow.yml
```
Mong đợi mỗi lệnh in `✔ Pipeline finished successfully`.

## Bước 4 — Xem trong UI
Mở `http://localhost:9002`:
- **Catalog** → tìm `public.orders`, `app.public.orders` (topic), DAG `lab13_pipeline`.
- **Schema** → click vào 1 dataset để xem column, descriptions.
- **Lineage** → xem upstream/downstream (nếu DAG Airflow có ghi lineage, các edge sẽ xuất hiện).

## Bước 5 — Governance actions
Chọn dataset `public.orders`:
1. **Owner** → Add owner (user hoặc group).
2. **Tags** → Add tag `PII`, `bronze`.
3. **Glossary** → Add glossary term (tạo mới `Customer Order`).

## Deliverables
- Ảnh `docker ps` (gồm container `datahub-*`).
- Ảnh DataHub catalog có ≥ 1 dataset + 1 topic + 1 DAG.
- Ảnh lineage view.
- Ảnh asset đã gán owner/tag/glossary.
- Trả lời 3 câu: metadata là gì, lineage giúp gì, governance khác management ở đâu.
- Khung submission: [`lab15_submission.md`](../lab15_submission.md).

## Self-check
- Một cột downstream báo sai — lineage giúp bạn quay lại root cause như thế nào?
- Khi nào business metadata quan trọng hơn technical metadata?
- Nếu không có catalog tập trung, team 50 người sẽ gặp vấn đề gì?
