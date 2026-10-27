from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_agent

# יצירת אפליקציית FastAPI
app = FastAPI()

# מתן הרשאה לממשק ה-React לשלוח בקשות לשרת
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


# הגדרת מבנה הנתונים שהשרת מקבל מהמשתמש
class TripRequest(BaseModel):
    region: str
    category: str
    hours: float = Field(gt=0)    # מספר שעות חייב להיות גדול מאפס
    budget: float = Field(ge=0)   # תקציב לא יכול להיות שלילי
    trip_date: date


# נתיב בסיסי לבדיקת תקינות פעולת השרת
@app.get("/")
def home():
    return {"message": "SmartTrip API is running!"}


# קבלת פרטי הטיול והפעלת סוכן ה-AI לתכנון המסלול
@app.post("/plan-trip")
def plan_trip(request: TripRequest):

    # העברת הנתונים לסוכן, שמפעיל כלים ומתכנן את הטיול
    result = run_agent(
        region=request.region,
        category=request.category,
        hours=request.hours,
        budget=request.budget,
        trip_date=request.trip_date.isoformat()
    )

    # הוספת תאריך הטיול לתוצאה בפורמט אחיד
    result["trip_date"] = request.trip_date.isoformat()

    # החזרת התוצאה לממשק המשתמש
    return result