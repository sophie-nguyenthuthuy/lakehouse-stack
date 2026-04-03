# Bài nộp Lab 16 — Feature Store Fundamentals with Feast

## 1. Kết quả chạy `feast apply`
Đã khởi tạo feature store bằng `feast init feature_repo` (sử dụng đối tượng `driver` theo mặc định).
Đầu ra terminal của lệnh đăng ký (apply) metadata.
```text
/Users/Thuy/lakehouse-stack/feast_env/lib/python3.9/site-packages/feast/feature_store.py:580: RuntimeWarning: On demand feature view is an experimental feature. This API is stable, but the functionality does not scale well for offline retrieval
  warnings.warn(
Created project feature_repo
Created entity driver
Created feature view driver_hourly_stats_fresh
Created feature view driver_hourly_stats
Created on demand feature view transformed_conv_rate_fresh
Created on demand feature view transformed_conv_rate
Created feature service driver_activity_v2
Created feature service driver_activity_v3
Created feature service driver_activity_v1

Created sqlite table feature_repo_driver_hourly_stats_fresh
Created sqlite table feature_repo_driver_hourly_stats
```

## 2. Kết quả materialize tính năng sang Online Store
Đầu ra của quá trình `feast materialize-incremental`:
```text
Materializing 2 feature views to 2026-04-03 09:54:18+00:00 into the sqlite online store.

driver_hourly_stats_fresh from 2026-04-02 09:54:20+00:00 to 2026-04-03 09:54:18+00:00:
100%|███████████████████████████████████████████████████████████████| 5/5 [00:00<00:00, 1208.66it/s]
driver_hourly_stats from 2026-04-02 09:54:20+00:00 to 2026-04-03 09:54:18+00:00:
100%|███████████████████████████████████████████████████████████████| 5/5 [00:00<00:00, 4626.41it/s]
```

## 3. Mã định nghĩa (`features.py` hoặc file equivalent là `example_repo.py`)
Mã nguồn định nghĩa cho source, entity, schema và feature view:

```python
from datetime import timedelta
import pandas as pd
from feast import (Entity, FeatureService, FeatureView, Field, FileSource, Project)
from feast.types import Float32, Float64, Int64

# Define a project for the feature repo
project = Project(name="feature_repo", description="A project for driver statistics")

# Define an entity for the driver.
driver = Entity(name="driver", join_keys=["driver_id"])

# Read data from parquet files in offline store
driver_stats_source = FileSource(
    name="driver_hourly_stats_source",
    path="data/driver_stats.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

# Define a Feature View allowing us to serve data to models online
driver_stats_fv = FeatureView(
    name="driver_hourly_stats",
    entities=[driver],
    ttl=timedelta(days=1),
    schema=[
        Field(name="conv_rate", dtype=Float32),
        Field(name="acc_rate", dtype=Float32),
        Field(name="avg_daily_trips", dtype=Int64, description="Average daily trips"),
    ],
    online=True,
    source=driver_stats_source,
    tags={"team": "driver_performance"},
)
```

## 4. Retrieving Online Features
Script lấy online features trả về thông tin theo độ trễ thấp từ online sqlite.
**Code test:**
```python
import pandas as pd
from feast import FeatureStore

store = FeatureStore(repo_path=".")

feature_vector = store.get_online_features(
    features=[
        "driver_hourly_stats:conv_rate",
        "driver_hourly_stats:acc_rate",
        "driver_hourly_stats:avg_daily_trips"
    ],
    entity_rows=[{"driver_id": 1001}]
).to_dict()

print("Online Feature for Driver 1001:")
print(feature_vector)
```

**Kết quả màn hình (Terminal Output nhận về model inputs):**
```text
Online Feature for Driver 1001:
{'driver_id': [1001], 'avg_daily_trips': [874], 'acc_rate': [0.18040895462036133], 'conv_rate': [0.9914646744728088]}
```


## 5. Trả lời câu hỏi kiến thức

**a. Offline vs online feature store khác nhau thế nào?**
- **Offline feature store:** Là kho lưu trữ dữ liệu tính năng với dung lượng lớn và có tính chất lịch sử (historical views). Store này chủ yếu phục vụ cho batch processing tĩnh như tạo batch training datasets để feed vào pipeline train model, hoặc các quá trình batch scoring inference. Yêu cầu của store này là read throughput cao với query phức tạp hơn là chú trọng vào độ phản hồi thấp.
- **Online feature store:** Là kho dữ liệu phục vụ riêng cho các model chạy real-time trong ứng dụng (sản phẩm phục vụ khách hàng trực tiếp, ví dụ fraud detection khi cà thẻ, hoặc recommender logic). Nó chỉ lưu các điểm latest value (giá trị mới nhất) của feature theo entity đó thay vì lưu nguyên lịch sử, nhằm đảm bảo thời gian truy vấn thấp (low-latency in milliseconds) để feed cho realtime inference request. Đổi lại năng lực phục vụ khối lượng dữ liệu lớn hay query historical data của online store bị giới hạn.

**b. Point-in-time correctness dùng để làm gì?**
Point-in-time (PIT) correctness là yêu cầu về độ chính xác thời gian cốt lõi dùng để **chống rò rỉ dữ liệu (data leakage) tới model trong thời điểm training**. 
Khi bạn lấy training set bằng cách build features từ offline store quanh các historic event. Feast hay feature store framework phải biết "Time travel" để khâu (join) chính xác feature values (ví dụ: total_in_bank_account) **nhỏ hơn hoặc đúng bằng timestamp lúc sự kiện xảy ra** (VD giao dịch diễn ra lúc 9:00AM), để không vô tình truyền những features vào lúc 9:01AM (future) cho model dự đoán cái chưa biết ở 9:00AM. Hiểu đơn giản PIT correctness ép tính năng model học là đúng với bối cảnh sự thực tại thời điểm phát sinh dự đoán.
