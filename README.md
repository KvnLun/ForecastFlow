# Weather Forecast Data Pipeline

A production-ready Apache Airflow data pipeline that fetches 5-day weather forecasts for major global cities and stores them in a PostgreSQL database. The pipeline runs daily and maintains historical weather forecast data for analysis.

## 🌟 Features

- **Automated Weather Data Collection**: Fetches weather forecasts from OpenWeatherMap API for 5 major cities
- **Two-Stage ETL Pipeline**: Separate DAGs for data extraction and loading
- **Robust Error Handling**: Comprehensive logging and error tracking
- **Duplicate Prevention**: Automatic handling of duplicate forecast entries
- **Dockerized Setup**: Fully containerized for easy deployment
- **Database Initialization**: Automated schema creation on first run

## 🏙️ Cities Covered

- New York, USA
- Los Angeles, USA
- Shanghai, China
- Tokyo, Japan
- Seoul, South Korea

## 📊 Data Collected

For each city, the pipeline collects:
- Temperature (current, feels like, min, max)
- Atmospheric pressure
- Humidity percentage
- Weather conditions (main category and description)
- Cloud coverage percentage
- Wind speed and direction
- Visibility
- Probability of precipitation (POP)
- Forecast timestamp

## 🏗️ Architecture

```
┌─────────────────────┐
│  fetch_weather_dag  │
│                     │
│  1. Geocode cities  │
│  2. Fetch forecasts │
│  3. Save to JSON    │
│  4. Trigger store   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ store_weather_dag   │
│                     │
│  1. Load JSON data  │
│  2. Validate cities │
│  3. Insert to DB    │
│  4. Handle dupes    │
└─────────────────────┘
```

## 🛠️ Tech Stack

- **Orchestration**: Apache Airflow 2.7.2
- **Database**: PostgreSQL 13
- **Container**: Docker & Docker Compose
- **API**: OpenWeatherMap API
- **Language**: Python 3.8+

## 📋 Prerequisites

- Docker Desktop installed and running
- OpenWeatherMap API key ([Get one free here](https://openweathermap.org/api))
- At least 4GB RAM allocated to Docker
- Windows/Mac/Linux with Docker Compose support

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/weather-forecast-pipeline.git
cd weather-forecast-pipeline
```

### 2. Project Structure

```
weather-forecast-pipeline/
├── dags/
│   ├── weather_fetch_dag.py       # Fetches weather data from API
│   └── weather_to_postgres_dag.py # Stores data in PostgreSQL
├── init-scripts/
│   └── init.sql                   # Database schema initialization
├── docker-compose.yml             # Container orchestration
└── README.md
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Generate a secret key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:
```env
AIRFLOW__WEBSERVER__SECRET_KEY=your-generated-key-here
```

### 4. Configure init-scripts Directory

Create the `init-scripts` folder and add your `init.sql` file:

```bash
mkdir init-scripts
# Move init.sql to init-scripts/
```

### 5. Start the Services

```bash
# Start all containers
docker-compose up -d

# Check if containers are running
docker ps
```

### 6. Initialize Airflow (First Run Only)

```bash
# Wait for airflow-init to complete
docker-compose logs -f airflow-init

# Once complete, restart services
docker-compose restart
```

### 7. Access Airflow Web UI

Open your browser and navigate to:
```
http://localhost:8080
```

**Default Credentials:**
- Username: `admin`
- Password: `admin`

### 8. Configure OpenWeatherMap API Key

1. In Airflow UI, go to **Admin → Variables**
2. Click **"+"** to add a new variable
3. Set:
   - **Key**: `OPENWEATHER_API_KEY`
   - **Val**: `your-api-key-here`
4. Click **Save**

### 9. Set Up Postgres Connection

1. In Airflow UI, go to **Admin → Connections**
2. Find or create connection with ID: `postgres_default`
3. Configure:
   - **Connection Type**: `Postgres`
   - **Host**: `postgres`
   - **Schema**: `airflow`
   - **Login**: `airflow`
   - **Password**: `airflow`
   - **Port**: `5432`
4. Click **Save**

### 10. Run the Pipeline

1. In the Airflow UI, go to **DAGs** page
2. Enable both DAGs:
   - `fetch_weather_dag`
   - `store_weather_dag`
3. Manually trigger `fetch_weather_dag` or wait for scheduled run

## 📊 Database Schema

### Cities Table
```sql
CREATE TABLE cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL UNIQUE
);
```

### Weather Forecasts Table
```sql
CREATE TABLE weather_forecasts (
    forecast_id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES cities(city_id),
    forecast_time TIMESTAMP NOT NULL,
    temperature DECIMAL(5,2),
    feels_like DECIMAL(5,2),
    temp_min DECIMAL(5,2),
    temp_max DECIMAL(5,2),
    pressure INTEGER,
    humidity INTEGER,
    weather_main VARCHAR(50),
    weather_description VARCHAR(200),
    clouds_percentage INTEGER,
    wind_speed DECIMAL(5,2),
    wind_direction INTEGER,
    visibility INTEGER,
    pop DECIMAL(3,2),
    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(city_id, forecast_time)
);
```

## 🔍 Monitoring & Debugging

### View DAG Logs

```bash
# View fetch DAG logs
docker exec airflow-scheduler cat /tmp/fetch_weather_debug.log

# View store DAG logs
docker exec airflow-scheduler cat /tmp/store_weather_debug.log
```

### Check Database Contents

```bash
# Connect to PostgreSQL
docker exec -it <postgres-container-name> psql -U airflow -d airflow

# View forecast count per city
SELECT 
    c.city_name,
    COUNT(*) as forecast_count,
    MIN(wf.forecast_time) as earliest_forecast,
    MAX(wf.forecast_time) as latest_forecast
FROM weather_forecasts wf
JOIN cities c ON wf.city_id = c.city_id
GROUP BY c.city_name
ORDER BY c.city_name;
```

### View Recent Forecasts

```sql
SELECT 
    c.city_name,
    wf.forecast_time,
    wf.temperature,
    wf.weather_description,
    wf.humidity
FROM weather_forecasts wf
JOIN cities c ON wf.city_id = c.city_id
ORDER BY wf.forecast_time DESC
LIMIT 20;
```

## 📅 Scheduling

Both DAGs are scheduled to run daily:
- **Schedule**: `@daily` (runs at midnight UTC)
- **Catchup**: Disabled (won't backfill historical runs)
- **Retries**: 1 attempt with 5-minute delay

To modify the schedule, edit the `schedule_interval` parameter in each DAG file.

## ⚙️ Configuration

### Add More Cities

1. Edit `weather_fetch_dag.py`
2. Update the `CITIES` list:
```python
CITIES = ["New York", "Los Angeles", "Shanghai", "Tokyo", "Seoul", "London", "Paris"]
```
3. Update `init.sql` to include the new cities
4. Restart Airflow scheduler

### Adjust Data Retention

Add a cleanup task to remove old forecasts:

```python
def cleanup_old_forecasts(**context):
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    # Delete forecasts older than 30 days
    cursor.execute("""
        DELETE FROM weather_forecasts 
        WHERE retrieved_at < NOW() - INTERVAL '30 days'
    """)
    conn.commit()
    cursor.close()
    conn.close()
```

## 🐛 Troubleshooting

### Issue: "Connection 'postgres_default' not found"
**Solution**: Create the Postgres connection in Airflow UI (Admin → Connections)

### Issue: "No weather data to insert"
**Solution**: 
1. Check if `fetch_weather_dag` ran successfully
2. Verify API key is set correctly
3. Check `/tmp/weather_data.json` exists in scheduler container

### Issue: "Cities table is empty"
**Solution**: 
1. Check if `init.sql` is in the `init-scripts` folder
2. Restart postgres container: `docker-compose restart postgres`

### Issue: Duplicate entries or "0 inserted"
**Solution**: This is normal behavior. The `ON CONFLICT DO NOTHING` clause prevents duplicates.

### Issue: 403 Forbidden on logs
**Solution**: Add secret key to environment variables in `docker-compose.yml`

## 📈 Future Enhancements

- [ ] Add front end interface to display weather conditions
- [ ] Add ability for users to select which cities are parsed and displayed
- [ ] Implement data quality checks
- [ ] Add email/Slack notifications on failures
- [ ] Store raw API responses for audit trail
- [ ] Add more cities dynamically from database
- [ ] Implement incremental updates instead of full refresh
- [ ] Add connection using REST API to get data from Postgres DB
- [ ] Create analytics views for trend analysis

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [OpenWeatherMap API](https://openweathermap.org/api) for weather data
- [Apache Airflow](https://airflow.apache.org/) for workflow orchestration
- [PostgreSQL](https://www.postgresql.org/) for reliable data storage

## 📧 Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter) - email@example.com

Project Link: [https://github.com/yourusername/weather-forecast-pipeline](https://github.com/yourusername/weather-forecast-pipeline)

---

⭐ **Star this repository if you find it helpful!**
