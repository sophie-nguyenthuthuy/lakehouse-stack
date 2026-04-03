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
