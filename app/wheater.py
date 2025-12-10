from fastapi import APIRouter
from datetime import datetime, time
import requests


# Tus coordenadas
LAT = -34.798358
LON = -58.357086


def is_night_mode():
    now = datetime.now().time()
    return now >= time(18, 0) or now <= time(4, 0)


def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}"
        "&hourly=temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m,precipitation_probability"
        "&past_days=1&forecast_days=2"
        "&timezone=auto"
    )

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


# ------------------ MULTIPLIERS ----------------------- #
def _summary(mult, rules, **values):
    """Helper para devolver el formato estándar."""
    return {
        "multiplier": max(0, min(mult, 2.5)),
        "details": {
            **values,
            "rules": rules
        },
    }


def compute_night_multiplier(data):
    hourly = data["hourly"]

    rain = sum(hourly["precipitation"][-24:])
    temp_max = max(hourly["temperature_2m"][-24:])
    wind_max = max(hourly["wind_speed_10m"][-24:])
    humidity = sum(hourly["relative_humidity_2m"][-24:]) / 24

    mult = 1.0
    rules = []

    # LLUVIA REAL
    if rain >= 40:
        return _summary(0.0, ["Lluvia >= 40 mm → mult = 0"],
                        rain_mm=rain, temp_max=temp_max, wind_max=wind_max, humidity_mean=humidity)
    if rain >= 5:
        mult *= 0.5
        rules.append("5-40 mm lluvia → mult *= 0.3")

    # CALOR
    if temp_max > 30:
        mult += 0.4
        rules.append("Temp > 30°C → +0.4")
    if temp_max > 35:
        mult += 0.3
        rules.append("Temp > 35°C → +0.3")

    # VIENTO
    if wind_max > 20:
        mult += 0.2
        rules.append("Viento > 20 km/h → +0.2")

    # HÚMEDO Y FRESCO
    if humidity > 70 and temp_max < 24:
        mult -= 0.3
        rules.append("Humedad > 70% y Temp < 24°C → -0.3")

    return _summary(mult, rules,
                    rain_mm=rain, temp_max=temp_max,
                    wind_max=wind_max, humidity_mean=humidity)


def compute_day_multiplier(data):
    hourly = data["hourly"]

    rain_fc = sum(hourly["precipitation"][:12])
    prob = max(hourly["precipitation_probability"][:12])
    temp_max = max(hourly["temperature_2m"][:12])
    wind_max = max(hourly["wind_speed_10m"][:12])
    humidity = sum(hourly["relative_humidity_2m"][:12]) / 12

    mult = 1.0
    rules = []

    # LLUVIA FUTURA
    if prob > 60 or rain_fc >= 10:
        return _summary(0.0, ["Prob > 60% o lluvia >= 10 mm → mult = 0"],
                        rain_forecast_mm=rain_fc, prob_precip=prob,
                        temp_max=temp_max, wind_max=wind_max, humidity_mean=humidity)

    if rain_fc >= 1:
        mult *= 0.5
        rules.append("1-10 mm lluvia → mult *= 0.3")

    # CALOR
    if temp_max > 30:
        mult += 0.3
        rules.append("Temp > 30°C → +0.3")
    if temp_max > 35:
        mult += 0.3
        rules.append("Temp > 35°C → +0.3")

    # VIENTO
    if wind_max > 20:
        mult += 0.2
        rules.append("Viento > 20 km/h → +0.2")

    # HÚMEDO Y FRESCO
    if humidity > 70 and temp_max < 24:
        mult -= 0.3
        rules.append("Humedad > 70% y Temp < 24°C → -0.3")

    return _summary(mult, rules,
                    rain_forecast_mm=rain_fc, prob_precip=prob,
                    temp_max=temp_max, wind_max=wind_max,
                    humidity_mean=humidity)

# ------------------ ENDPOINT --------------------------- #


weather_router = APIRouter()


@weather_router.get("/weather-multiplier")
def weather_multiplier():
    data = fetch_weather()
    if is_night_mode():
        response = compute_night_multiplier(data)
        response["mode"] = "night (historic)"
    else:
        response = compute_day_multiplier(data)
        response["mode"] = "day (forecast)"

    return response
