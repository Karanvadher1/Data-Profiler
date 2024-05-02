from datetime import datetime, timedelta
import json
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text,Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
from airflow.models import Variable
import pandas as pd
import numpy as np
from airflow.models import DagRun
from psycopg2.extensions import register_adapter, AsIs
register_adapter(np.int64, AsIs)


# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2022, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'schedule': None
}


# # Define the DAG
# dag = DAG(
#     'etl_pipeline',
#     default_args=default_args,
#     description='A simple MySQL data pipeline',
#     schedule=None,  # Adjust based on your needs
# )

def schedule_dag(**kwargs):
    schedule_value = kwargs['dag_run'].conf.get('schedule')
    print(schedule_value)
    return schedule_value


with DAG('etl_pipeline', default_args=default_args) as dag:
    task_schedule_dag = PythonOperator(
        task_id='schedule_dag',
        python_callable=schedule_dag,
        provide_context=True
    )


def fetch_data(**kwargs):
    service_name = kwargs['dag_run'].conf.get('service_name')
    table = kwargs['dag_run'].conf.get('selected_table')
    db = kwargs['dag_run'].conf.get('db')
    username = kwargs['dag_run'].conf.get('username')
    host = kwargs['dag_run'].conf.get('host')
    password = kwargs['dag_run'].conf.get('password')
    source_engine = None
    print("fetched the date of the user are thew :", {service_name},{table},{db},{username})
    
    if service_name == 'mysql':
        mysql_conn_str = f"mysql+mysqlconnector://{username}:{password}@{host}:3306/{db}"
        source_engine = create_engine(mysql_conn_str)
    if service_name == 'postgresql':
        postgres_conn_str = f"postgresql://{username}:{password}@{host}:5432/{db}"
        source_engine = create_engine(postgres_conn_str)
    
    if source_engine:
        print("connected")
        with source_engine.connect() as connection:
            sql_query = text(f'SELECT * FROM {table}')
            result = connection.execute(sql_query).fetchall()
            # Convert SQLAlchemy Row objects to dictionaries
            serialized_data = [dict(row) for row in result]
            # Push the serialized data to XCom
            kwargs['ti'].xcom_push(key='source_data', value=serialized_data)

            # Do something with the data (e.g., print it)
task_fetch_data = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_data,
    # provide_context=True,
    dag=dag,
)

# Task 3: Format data (example PythonOperator)
def format_data(**kwargs):
    # Retrieve data from XCom
    source_data = kwargs['ti'].xcom_pull(task_ids='fetch_data', key='source_data')
    print(f"Retrieved source_data: {source_data}")

task_format_data = PythonOperator(
    task_id='format_data',
    python_callable=format_data,
    # provide_context=True,
    dag=dag,
)

# Task 4: Calculate metrics (example PythonOperator)
def calculate_metrics_dag(**kwargs):
    table = kwargs['dag_run'].conf.get('selected_table')
    connector = kwargs['dag_run'].conf.get('connector')
    user = kwargs['dag_run'].conf.get('user')
    ingestion_id = kwargs['dag_run'].conf.get('ingestion_id')
    
    ti = kwargs['ti']
    dataset = ti.xcom_pull(task_ids='fetch_data', key='source_data')

    # dataset = kwargs.get('source_data')
    if dataset is not None:    
        print(f"Calculating metrics for entire dataset")
        df = pd.DataFrame(dataset)
        # Remaining code for metrics calculation...

        # Filter out non-numeric columns
        numeric_columns = df.select_dtypes(include=np.number)
        
        # Check if there are any numeric columns to proceed
        if numeric_columns.empty:
            print("No numeric columns found. Skipping standard deviation calculation.")
            return

        # Calculate metrics
        num_rows = df.shape[0]
        num_columns = df.shape[1]
        num_duplicate_rows = df.duplicated().sum()
        null_values_per_column = df.isnull().sum()
        std_per_column = numeric_columns.std()

        # Convert Pandas Series to a dictionary with simple types
        std_per_column_dict = std_per_column.to_dict()

        # Convert any non-serializable values (e.g., numpy types) to simple types
        std_per_column_dict = {str(key): float(value) for key, value in std_per_column_dict.items()}

        # null_values_per_column_json = json.dumps(null_values_per_column.to_dict())
        null_values_per_column_json = json.dumps(null_values_per_column.to_dict())

        # Convert std_per_column_dict to a JSON string
        std_per_column_dict_json = json.dumps(std_per_column_dict)

        #get dag status
        dag_runs = DagRun.find(dag_id='etl_pipeline')
        final_status = None
        if dag_runs:
            final_status = dag_runs[0].get_state()
        print(final_status)

        # Print the metrics
        print(f"Number of Rows: {num_rows}")
        print(f"Number of Columns: {num_columns}")
        print(f"Number of Duplicate Rows: {num_duplicate_rows}")
        print(f"Null Values per Column:{null_values_per_column}")
        print(f"Standard Deviation per Numeric Column:{std_per_column_dict}")

        #craeting postgress connection to website database
        postgres_conn_str = f"postgresql+psycopg2://postgres:postgres@localhost:5432/Dataprofiler"
        source_engine = create_engine(postgres_conn_str)
        if source_engine:            
            print("connected postgress database")
            with source_engine.connect() as connection:
                try:
                    # Execute the insert query
                    connection.execute("""
                        INSERT INTO connectors_matrix (
                            dataset, num_rows, num_columns, num_duplicate_rows, null_values_per_column,std_per_column_dict, ingestion_id,connector_id, user_id,status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s,%s)""",
                        (table, num_rows, num_columns, num_duplicate_rows, null_values_per_column_json,std_per_column_dict_json, ingestion_id,connector, user,final_status))
                    print("Data stored successfully")
                except Exception as e:
                    print(f"Failed to store data: {e}")
        return {
            'num_rows': num_rows,
            'num_columns': num_columns,
            'num_duplicate_rows': num_duplicate_rows,
            'null_values_per_column': null_values_per_column.to_dict(),  # Convert Series to dict
            'std_per_column': std_per_column_dict
        }
        
    else:
        print("Error:perameter is pending")

task_calculate_metrics = PythonOperator(
    task_id='calculate_metrics',
    python_callable=calculate_metrics_dag,
    # provide_context=True,
    dag=dag,
)

# Define task dependencies
task_schedule_dag >> task_fetch_data >> task_format_data >> task_calculate_metrics