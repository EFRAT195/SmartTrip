
import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


REGION_COORDINATES = {
    "ירושלים": (31.7683, 35.2137),
    "צפון": (32.7940, 35.5312),
    "מרכז": (32.0853, 34.7818),
}


def get_weather(region: str, trip_date: str) -> dict:
    coordinates = REGION_COORDINATES.get(region)

    if coordinates is None:
        return {
            "available": False,
            "reason": "אזור לא מוכר"
        }

    try:
        requested_date = date.fromisoformat(trip_date)
    except ValueError:
        return {
            "available": False,
            "reason": "תאריך לא תקין"
        }

    today = date.today()

    if requested_date < today:
        return {
            "available": False,
            "reason": "לא ניתן לקבל תחזית עתידית לתאריך שעבר"
        }

    if requested_date > today + timedelta(days=15):
        return {
            "available": False,
            "reason": "התאריך רחוק מדי לקבלת תחזית"
        }

    latitude, longitude = coordinates

    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max,"
            "weather_code"
        ),
        "timezone": "Asia/Jerusalem",
        "forecast_days": 16
    })

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + params
    )

    try:
        with urlopen(url, timeout=10) as response:
            data = json.load(response)

        daily = data["daily"]
        index = daily["time"].index(trip_date)

        return {
            "available": True,
            "region": region,
            "date": trip_date,
            "temperature_max": daily["temperature_2m_max"][index],
            "temperature_min": daily["temperature_2m_min"][index],
            "rain_probability": daily[
                "precipitation_probability_max"
            ][index],
            "weather_code": daily["weather_code"][index]
        }

    except (URLError, HTTPError, TimeoutError):
        return {
            "available": False,
            "reason": "לא ניתן להתחבר לשירות מזג האוויר"
        }

    except (KeyError, ValueError, IndexError, TypeError):
        return {
            "available": False,
            "reason": "לא נמצאה תחזית לתאריך המבוקש"
        }
