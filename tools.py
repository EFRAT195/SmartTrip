import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "attractions.json"


def search_attractions(region, category):
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        attractions = json.load(file)

    return [
        attraction
        for attraction in attractions
        if attraction["region"] == region
        and attraction["category"] == category
    ]


def check_trip(attractions, max_hours, max_budget):
    total_hours = sum(a["duration"] for a in attractions)
    total_price = sum(a["price"] for a in attractions)

    return {
        "valid": total_hours <= max_hours and total_price <= max_budget,
        "total_hours": total_hours,
        "total_price": total_price,
        "time_exceeded": total_hours > max_hours,
        "budget_exceeded": total_price > max_budget
    }