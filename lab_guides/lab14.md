# Lab 14 — Data Quality with Great Expectations + Deequ

## Objectives
- Phân loại 5 data quality dimensions: completeness, accuracy, consistency, timeliness, validity.
- Dùng Great Expectations để viết ≥ 3 rule-based checks.
- Liệt kê Deequ-style statistical metrics: completeness, uniqueness, distribution, size.
- Thiết kế DAG đặt gate validation giữa ingest → transform → publish.

## Prerequisites
Python 3.10+, không cần Docker cho Phần A.
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas 'great_expectations>=0.18'
```

## Phần A — Great Expectations (rule-based)

### Bước A1 — Review script
File: [`ge_validate.py`](../ge_validate.py). Nó đọc `orders.csv` từ repo root và áp các expectation:

| Rule                                         | Dimension    |
|----------------------------------------------|--------------|
| `expect_column_values_to_not_be_null(order_id)`  | completeness |
| `expect_column_values_to_be_unique(order_id)`    | accuracy     |
| `expect_column_values_to_not_be_null(customer_id)`| completeness |
| `expect_column_values_to_be_between(quantity,1,20)`| validity    |
| `expect_column_values_to_be_between(unit_price,0,1000)`| validity |
| `expect_column_values_to_be_in_set(order_status, {...})`| consistency |
| `expect_table_row_count_to_be_between(1, 100000)`| size        |

### Bước A2 — Run
```bash
python3 ge_validate.py
```
Mong đợi: `success: True/False` cùng danh sách expectation pass/fail. Nếu `orders.csv` chứa dòng bẩn cố ý → ít nhất 1 rule fail.

## Phần B — Deequ-style metrics trên Spark
Deequ full runtime cần Scala; ở lab này ta discuss metric và mô phỏng trong PySpark:

```python
from pyspark.sql import SparkSession, functions as F
spark = SparkSession.builder.appName("dq-lab").getOrCreate()
df = spark.read.option("header", True).csv("orders.csv")

# completeness
df.selectExpr("avg(case when order_id is not null then 1.0 else 0.0 end) as completeness_order_id").show()
# uniqueness
df.select(F.count("*").alias("rows"),
          F.countDistinct("order_id").alias("distinct_order_id")).show()
# distribution
df.select(F.min("quantity"), F.max("quantity"), F.avg("quantity")).show()
# size
print("row_count:", df.count())
```

## Phần C — Airflow gate (design)
DAG khung:
```python
ingest >> ge_validate >> transform >> publish
```
Cài `trigger_rule=all_success` cho `transform` → nếu `ge_validate` fail, `transform` skip, giữ bronze sạch khỏi silver/gold.

## Deliverables
- Script/notebook GE đã chạy.
- Screenshot hoặc text output showing pass + fail expectations.
- Danh sách Deequ metrics bạn sẽ monitor + lý do (completeness, uniqueness, distribution, size).
- DAG snippet / design showing vị trí gate validation.
- Khung submission: [`lab14_submission.md`](../lab14_submission.md).

## Self-check
- Rule-based khác statistical ở đâu? Bài toán nào cần mỗi loại?
- Bạn bắt bug ở Bronze hay Gold thì rẻ hơn? Vì sao?
- Làm sao để 1 bronze load sai không làm hỏng silver/gold downstream?
