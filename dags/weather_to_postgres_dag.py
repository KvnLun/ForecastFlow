from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook
from datetime import datetime, timedelta
import json
import traceback
import os

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

TEMP_FILE = "/tmp/weather_data.json"
DEBUG_LOG = "/tmp/store_weather_debug.log"


def log_to_file(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(DEBUG_LOG, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)


def store_weather_data(**context):
    log_to_file("=" * 80)
    log_to_file("Starting store_weather_data task")
    
    # Check if file exists
    if not os.path.exists(TEMP_FILE):
        log_to_file(f"ERROR: File not found {TEMP_FILE}")
        log_to_file(f"Files in /tmp: {os.listdir('/tmp')}")
        raise FileNotFoundError(f"Weather data file not found: {TEMP_FILE}")
    
    log_to_file(f"File found: {TEMP_FILE}")
    log_to_file(f"File size: {os.path.getsize(TEMP_FILE)} bytes")

    # Load data
    with open(TEMP_FILE, 'r') as f:
        weather_data = json.load(f)

    if not weather_data:
        log_to_file("WARNING: No data to insert (empty list)")
        return

    log_to_file(f"Loaded {len(weather_data)} records from file")
    log_to_file(f"Sample record: {weather_data[0]}")

    # Connect to Postgres
    try:
        log_to_file("Connecting to Postgres...")
        pg_hook = PostgresHook(postgres_conn_id="postgres_default")
        conn = pg_hook.get_conn()
        cursor = conn.cursor()
        log_to_file("Connected successfully")
    except Exception as e:
        log_to_file(f"ERROR: Failed to connect to Postgres: {e}")
        raise

    # Check if cities exist
    log_to_file("\nChecking cities table...")
    try:
        cursor.execute("SELECT city_id, city_name FROM cities;")
        cities_in_db = cursor.fetchall()
        log_to_file(f"Cities in database: {cities_in_db}")
        
        if not cities_in_db:
            log_to_file("ERROR: No cities found in database!")
            log_to_file("You need to populate the cities table first")
            cursor.close()
            conn.close()
            raise ValueError("Cities table is empty")
            
    except Exception as e:
        log_to_file(f"ERROR querying cities table: {e}")
        raise

    # Check for existing forecasts
    try:
        cursor.execute("SELECT COUNT(*) FROM weather_forecasts;")
        existing_count = cursor.fetchone()[0]
        log_to_file(f"Existing forecasts in DB: {existing_count}")
    except Exception as e:
        log_to_file(f"ERROR checking weather_forecasts: {e}")

    # Insert data
    insert_sql = """
    INSERT INTO weather_forecasts (
        city_id, forecast_time, temperature, feels_like, temp_min, temp_max,
        pressure, humidity, weather_main, weather_description,
        clouds_percentage, wind_speed, wind_direction, visibility, pop
    )
    SELECT c.city_id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    FROM cities c
    WHERE c.city_name = %s
    ON CONFLICT (city_id, forecast_time) DO NOTHING;
    """

    inserted_count = 0
    skipped_count = 0
    error_count = 0
    
    log_to_file("\nStarting inserts...")
    
    for i, record in enumerate(weather_data):
        try:
            # Log every 10th record
            if i % 10 == 0:
                log_to_file(f"Processing record {i}/{len(weather_data)}: {record['city']} at {record['forecast_time']}")
            
            cursor.execute(insert_sql, (
                record["forecast_time"],
                record["temperature"],
                record["feels_like"],
                record["temp_min"],
                record["temp_max"],
                record["pressure"],
                record["humidity"],
                record["weather_main"],
                record["weather_description"],
                record["clouds_percentage"],
                record["wind_speed"],
                record["wind_direction"],
                record["visibility"],
                record["pop"],
                record["city"]
            ))
            
            # Check if row was actually inserted
            if cursor.rowcount > 0:
                inserted_count += 1
            else:
                skipped_count += 1
                if i < 5:  # Log first few skips
                    log_to_file(f"Skipped (duplicate or city not found): {record['city']} at {record['forecast_time']}")
                
        except Exception as e:
            error_count += 1
            log_to_file(f"ERROR inserting record {i}: {record}")
            log_to_file(f"Error: {e}")
            if error_count < 3:  # Only print full traceback for first few errors
                log_to_file(traceback.format_exc())

    # Commit
    try:
        conn.commit()
        log_to_file("\nCommit successful")
    except Exception as e:
        log_to_file(f"ERROR: Commit failed: {e}")
        conn.rollback()
        raise

    # Final count check
    try:
        cursor.execute("SELECT COUNT(*) FROM weather_forecasts;")
        final_count = cursor.fetchone()[0]
        log_to_file(f"\nFinal count in DB: {final_count}")
        log_to_file(f"New records added: {final_count - existing_count}")
    except Exception as e:
        log_to_file(f"ERROR checking final count: {e}")

    cursor.close()
    conn.close()
    
    log_to_file("\n" + "=" * 80)
    log_to_file("SUMMARY:")
    log_to_file(f"  Total records processed: {len(weather_data)}")
    log_to_file(f"  Successfully inserted: {inserted_count}")
    log_to_file(f"  Skipped (duplicates/not found): {skipped_count}")
    log_to_file(f"  Errors: {error_count}")
    log_to_file("=" * 80)


with DAG(
    "store_weather_dag",
    default_args=default_args,
    description="Store fetched weather data into Postgres",
    schedule_interval="@daily",
    start_date=datetime(2025, 11, 12),
    catchup=False,
    tags=["weather", "postgres"],
) as dag:

    store_task = PythonOperator(
        task_id="store_weather",
        python_callable=store_weather_data,
        provide_context=True
    )