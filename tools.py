import json
from pathlib import Path

# הגדרת הנתיב לקובץ המכיל את מאגר האטרקציות
DATA_FILE = Path(__file__).parent / "attractions.json"


# חיפוש אטרקציות המתאימות לאזור ולסוג הטיול שהמשתמש בחר
def search_attractions(region, category):

    # קריאת נתוני האטרקציות מקובץ JSON
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        attractions = json.load(file)

    # סינון והחזרת האטרקציות שעומדות בשני התנאים
    return [
        attraction
        for attraction in attractions
        if attraction["region"] == region
        and attraction["category"] == category
    ]


# בדיקה האם המסלול שהסוכן בחר עומד במגבלות הזמן והתקציב
def check_trip(attractions, max_hours, max_budget):

    # חישוב משך הביקור הכולל והעלות הכוללת של האטרקציות
    total_hours = sum(a["duration"] for a in attractions)
    total_price = sum(a["price"] for a in attractions)

    # החזרת תוצאות הבדיקה כדי שהסוכן יוכל להחליט אם לאשר או לשנות את המסלול
    return {
        "valid": total_hours <= max_hours and total_price <= max_budget,
        "total_hours": total_hours,
        "total_price": total_price,
        "time_exceeded": total_hours > max_hours,
        "budget_exceeded": total_price > max_budget
    }