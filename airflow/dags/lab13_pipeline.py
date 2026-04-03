from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.python import PythonSensor
from datetime import datetime, timedelta

def check_data_ready():
    print("Checking if input data is ready...")
    return True

def validate():
    print("Validating input data...")
    pass

default_args = {
    'owner': 'admin',
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    dag_id="lab13_end_to_end_pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=['lab13']
) as dag:

    # 1. Sensor
    wait_for_data = PythonSensor(
        task_id="wait_for_input_data",
        python_callable=check_data_ready,
        mode="poke",
        timeout=600,
        poke_interval=10
    )

    # 2. Ingest (BashOperator)
    ingest = BashOperator(
        task_id="ingest_data",
        bash_command="echo 'Ingesting data from source...'"
    )

    # 3. Validate (PythonOperator)
    validate_task = PythonOperator(
        task_id="validate_data",
        python_callable=validate
    )

    # 4. Transform
    transform = BashOperator(
        task_id="transform_data",
        bash_command="echo 'Transforming data...'"
    )

    # 5. Publish
    publish = BashOperator(
        task_id="publish_data",
        bash_command="echo 'Publishing to Gold layer...'",
        trigger_rule="all_success"
    )

    # Explicit Dependency
    wait_for_data >> ingest >> validate_task >> transform >> publish
