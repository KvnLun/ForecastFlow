-- Create cities table first since weather_forecasts references it
CREATE TABLE IF NOT EXISTS cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL UNIQUE
);

-- Insert your 5 cities (New York, LA, Shanghai, Tokyo, Seoul)
INSERT INTO cities (city_name) VALUES
('New York'),
('Los Angeles'),
('Shanghai'),
('Tokyo'),
('Seoul')
ON CONFLICT (city_name) DO NOTHING;

-- Create weather_forecasts table
CREATE TABLE IF NOT EXISTS weather_forecasts (
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
