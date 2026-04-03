import pandas as pd
import great_expectations as gx

# Read sample data
orders = pd.read_csv("orders.csv")

# Create Ephemeral GE Context
context = gx.get_context(mode="ephemeral")
source = context.sources.add_pandas(name="bootcamp_source")
asset = source.add_dataframe_asset(name="orders_asset")
batch = asset.build_batch_request(dataframe=orders)

# Note: Using create_expectation_suite instead of assuming orders_suite exists
context.add_or_update_expectation_suite("orders_suite")
validator = context.get_validator(batch_request=batch, expectation_suite_name="orders_suite")

# Task A2. Add common expectations
validator.expect_column_values_to_not_be_null("order_id")
validator.expect_column_values_to_be_unique("order_id")
validator.expect_column_values_to_not_be_null("customer_id")
validator.expect_column_values_to_be_between("quantity", min_value=1, max_value=20)
validator.expect_column_values_to_be_between("unit_price", min_value=0, max_value=1000)
validator.expect_column_values_to_be_in_set(
    "order_status",
    ["created", "paid", "shipped", "delivered", "cancelled"]
)
validator.expect_table_row_count_to_be_between(min_value=1, max_value=100000)

# Task A3. Run validation and review result
result = validator.validate()
print("Success:", result["success"])
print("Validation Results Detailed:")

for res in result["results"]:
    if not res["success"]:
        print(f"FAILED: {res['expectation_config']['expectation_type']} on {res['expectation_config']['kwargs'].get('column', 'table')}")
        print(f"  --> Unexpected items: {res['result'].get('unexpected_list', [])}")
    else:
        print(f"PASSED: {res['expectation_config']['expectation_type']} on {res['expectation_config']['kwargs'].get('column', 'table')}")

