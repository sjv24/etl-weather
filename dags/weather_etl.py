from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import psycopg2
import os


# Retrieve API key from environment variable (set via Docker Compose)
API_KEY = os.getenv("OPENWEATHER_API_KEY")

# List of major Indian cities with coordinates for accurate weather data
INDIAN_CITIES = [
    {"name": "Delhi", "lat": 28.7041, "lon": 77.1025},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"name": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"name": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    {"name": "Lucknow", "lat": 26.8467, "lon": 80.9462},
    {"name": "Gandhinagar", "lat": 23.2156, "lon": 72.6369},
    {"name": "Thiruvananthapuram", "lat": 8.5241, "lon": 76.9366},
    {"name": "Jaipur", "lat": 26.9124, "lon": 75.7873},
    {"name": "Amaravati", "lat": 16.5417, "lon": 80.5150},
    {"name": "Bhopal", "lat": 23.2599, "lon": 77.4126}
]


# Function to fetch current weather data from OpenWeatherMap
def fetch_weather(lat, lon, city_name):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    weather = {
        "city": city_name,
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        "date": datetime.utcnow().date()
    }
    return weather


# Function to connect to PostgreSQL and store weather data
def store_weather():
    import logging

    # Connect to PostgreSQL container (host is service name in Docker Compose)
    conn = psycopg2.connect(
        host="postgres",
        database= os.getenv("POSTGRES_DB"),
        user= os.getenv("POSTGRES_USER"),
        password= os.getenv("POSTGRES_PASSWORD")
    )
    cur = conn.cursor()

    for city in INDIAN_CITIES:
        try:
            # Fetch and log weather data
            weather = fetch_weather(city["lat"], city["lon"], city["name"])
            logging.info(f"Fetched weather for {city['name']}: {weather}")

            # Insert weather data into the weather table
            insert_query = """
            INSERT INTO weather (city, temperature, humidity, weather_description, date)
            VALUES (%s, %s, %s, %s, %s)
            """
            cur.execute(insert_query, (
                weather["city"],
                weather["temperature"],
                weather["humidity"],
                weather["description"],
                weather["date"]
            ))

            logging.info(f"Inserted weather for {city['name']} successfully.")
        except Exception as e:
            logging.error(f"Error with {city['name']}: {e}")

    conn.commit()
    cur.close()
    conn.close()


# Define Airflow DAG
default_args = {
    "start_date": datetime(2024, 1, 1),
}

# DAG definition: runs daily and triggers weather fetch/store task
with DAG(
    dag_id="weather_etl",
    schedule_interval="@daily",
    default_args=default_args,
    catchup=False
) as dag:
    
    store_weather_task = PythonOperator(
        task_id="store_weather",
        python_callable=store_weather
    )

    store_weather_task
