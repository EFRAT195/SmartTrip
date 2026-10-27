
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class TripRequest(BaseModel):
    region: str
    category: str
    hours: float = Field(gt=0)
    budget: float = Field(ge=0)
    trip_date: date


@app.get("/")
def home():
    return {"message": "SmartTrip API is running!"}


@app.post("/plan-trip")
def plan_trip(request: TripRequest):
    result = run_agent(
        region=request.region,
        category=request.category,
        hours=request.hours,
        budget=request.budget,
        trip_date=request.trip_date.isoformat()
    )

    result["trip_date"] = request.trip_date.isoformat()

    return result
