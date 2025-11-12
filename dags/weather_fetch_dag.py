from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import requests
import json
import traceback
import os

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

CITIES = ["New York", "Los Angeles", "Shanghai", "Tokyo", "Seoul"]
GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
TEMP_FILE = "/tmp/weather_data.json"


def log_to_file(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open("/tmp/fetch_weather_debug.log", 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)


def fetch_weather_data(**context):
    log_to_file("Starting fetch_weather_data task")
    try:
        api_key = Variable.get("OPENWEATHER_API_KEY")
    except Exception as e:
        log_to_file(f"ERROR: Could not get API key: {e}")
        raise

    all_weather_data = []

    for city in CITIES:
        try:
            geo_params = {"q": city, "limit": 1, "appid": api_key}
            geo_resp = requests.get(GEOCODE_URL, params=geo_params, timeout=10)
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            if not geo_data:
                log_to_file(f"No coordinates found for {city}")
                continue

            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

            forecast_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
            forecast_resp = requests.get(FORECAST_URL, params=forecast_params, timeout=10)
            forecast_resp.raise_for_status()
            forecast_data = forecast_resp.json()

            for entry in forecast_data.get("list", []):
                all_weather_data.append({
                    "city": city,
                    "forecast_time": entry.get("dt_txt"),
                    "temperature": entry["main"].get("temp"),
                    "feels_like": entry["main"].get("feels_like"),
                    "temp_min": entry["main"].get("temp_min"),
                    "temp_max": entry["main"].get("temp_max"),
                    "pressure": entry["main"].get("pressure"),
                    "humidity": entry["main"].get("humidity"),
                    "weather_main": entry["weather"][0].get("main") if entry.get("weather") else None,
                    "weather_description": entry["weather"][0].get("description") if entry.get("weather") else None,
                    "clouds_percentage": entry.get("clouds", {}).get("all"),
                    "wind_speed": entry.get("wind", {}).get("speed"),
                    "wind_direction": entry.get("wind", {}).get("deg"),
                    "visibility": entry.get("visibility"),
                    "pop": entry.get("pop")
                })

        except Exception as e:
            log_to_file(f"ERROR fetching data for {city}: {e}")
            log_to_file(traceback.format_exc())

    with open(TEMP_FILE, 'w') as f:
        json.dump(all_weather_data, f)
    log_to_file(f"Weather data saved to {TEMP_FILE}")


with DAG(
    "fetch_weather_dag",
    default_args=default_args,
    description="Fetch 5-day forecast for 5 cities",
    schedule_interval="@daily",
    start_date=datetime(2025, 11, 12),
    catchup=False,
    tags=["weather", "api"],
) as dag:

    fetch_task = PythonOperator(
        task_id="fetch_weather",
        python_callable=fetch_weather_data,
        provide_context=True
    )

    trigger_store = TriggerDagRunOperator(
        task_id="trigger_store_weather_dag",
        trigger_dag_id="store_weather_dag",
        wait_for_completion=False,  # set True if you want fetch to wait for store to finish
        poke_interval=60,
    )

    fetch_task >> trigger_store
