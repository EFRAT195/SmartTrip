
import json
from openai import OpenAI
from dotenv import load_dotenv
from tools import search_attractions, check_trip
from weather_tool import get_weather

load_dotenv()
client = OpenAI()

# הכלים שהסוכן יכול לבחור להפעיל
TOOLS = [
    {
        "type": "function",
        "name": "search_attractions",
        "description": "Search for attractions by region and category",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "category": {"type": "string"}
            },
            "required": ["region", "category"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "check_trip",
        "description": "Validate a trip against time and budget limits",
        "parameters": {
            "type": "object",
            "properties": {
                "attraction_ids": {
                    "type": "array",
                    "items": {"type": "integer"}
                },
                "max_hours": {"type": "number"},
                "max_budget": {"type": "number"}
            },
            "required": [
                "attraction_ids",
                "max_hours",
                "max_budget"
            ],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get a real weather forecast for a region and date",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "trip_date": {"type": "string"}
            },
            "required": ["region", "trip_date"],
            "additionalProperties": False
        },
        "strict": True
    }
]

# מבנה הפלט הסופי: המודל חייב להחזיר ציוד והסברים בפורמט קבוע
FINAL_FORMAT = {
    "type": "json_schema",
    "name": "trip_recommendations",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string"
            },
            "equipment": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["name", "reason"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["summary", "equipment"],
        "additionalProperties": False
    }
}


def run_agent(region, category, hours, budget, trip_date):
    attractions_by_id = {}
    last_validation = None
    weather_result = None
    logs = []

    instructions = """
You are SmartTrip, an autonomous trip planning agent.

Create a trip that fits the user's region, category,
available time, budget and date.

Available tools:
1. search_attractions - find attractions.
2. check_trip - validate a proposed trip.
3. get_weather - retrieve a real weather forecast.

Trip planning rules:
- First search for attractions using the user's exact filters.
- Select attractions only from the search results.
- Validate the selection using check_trip.
- If validation fails, adjust the selection and check again.
- Never invent attractions or IDs.
- Never change the user's limits.
- Never select duplicate attractions.
- Never validate an empty trip.
- Only announce success after successful validation.
- If no suitable trip exists, explain why.

Weather rules:
- After validating a successful trip, call get_weather.
- Use the exact region and date provided by the user.
- Never invent weather information.
- If the forecast is unavailable, do not guess the weather.
- If conditions could make an outdoor trip unsafe,
  warn the user.

Equipment rules:
- Analyze the actual selected attractions.
- Recommend relevant equipment based on the attractions
  and the weather forecast, when available.
- Explain the reason for every recommended item.
- Do not recommend irrelevant equipment.
- If weather is unavailable, recommendations may rely
  on the selected attractions, but not on guessed weather.
- Answer in Hebrew.
"""

    messages = [
        {
            "role": "user",
            "content": (
                f"Plan a trip in {region}, "
                f"category {category}, "
                f"maximum {hours} hours and {budget} ILS. "
                f"Trip date: {trip_date}."
            )
        }
    ]

    # לולאת הסוכן: בחירת כלי, קבלת תוצאה והחלטה על הפעולה הבאה
    for step in range(12):
        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=instructions,
            input=messages,
            tools=TOOLS
        )

        messages.extend(response.output)

        calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not calls:
            # מסלול מוצלח חייב לעבור בדיקה וגם ניסיון לקבל תחזית
            success = (
                last_validation is not None
                and last_validation.get("valid") is True
                and bool(last_validation.get("attractions"))
            )

            if success and weather_result is None:
                messages.append({
                    "role": "user",
                    "content": (
                        "The trip is validated. "
                        "Call get_weather before finishing."
                    )
                })
                continue

            # אחרי שהכלים סיימו, מבקשים מהמודל פלט JSON מובנה
            final_response = client.responses.create(
                model="gpt-4o-mini",
                instructions=(
                    instructions
                    + """

Return a JSON object:
- summary: a short Hebrew explanation of the trip
  and weather, or why planning failed.
- equipment: relevant equipment recommendations,
  each with a Hebrew name and reason.
If the trip is invalid, return an empty equipment list.
Do not invent weather data.
"""
                ),
                input=messages + [
                    {
                        "role": "user",
                        "content": (
                            "Provide the final structured response "
                            "using the validated trip and weather "
                            "tool results already provided."
                        )
                    }
                ],
                text={
                    "format": FINAL_FORMAT
                },
                tool_choice="none"
            )

            # המודל מחזיר מחרוזת JSON, ואנחנו ממירים אותה למילון Python
            recommendations = json.loads(
                final_response.output_text
            )

            equipment = (
                recommendations["equipment"]
                if success
                else []
            )

            logs.append({
                "action": "equipment",
                "title": "התאמת ציוד לטיול",
                "description": (
                    f"הסוכן בחר {len(equipment)} פריטי ציוד "
                    f"בהתאם למסלול ולתחזית הזמינה."
                    if success
                    else "לא נוצר מסלול תקין להתאמת ציוד."
                ),
                "success": success
            })

            return {
                "success": success,
                "result": recommendations["summary"],
                "logs": logs,
                "trip": last_validation if success else None,
                "weather": weather_result,
                "equipment": equipment
            }

        # מפעילים בפועל את הכלי שהמודל ביקש
        for call in calls:
            args = json.loads(call.arguments)

            if call.name == "search_attractions":
                result = search_attractions(region, category)

                attractions_by_id = {
                    attraction["id"]: attraction
                    for attraction in result
                }

                last_validation = None
                weather_result = None

                logs.append({
                    "action": "search",
                    "title": "חיפוש אטרקציות",
                    "description": (
                        f"נמצאו {len(result)} אטרקציות "
                        f"באזור {region}, בקטגוריית {category}."
                    ),
                    "success": True
                })

            elif call.name == "check_trip":
                ids = args["attraction_ids"]

                # מונעים שימוש באטרקציות שלא נמצאו או בחירה כפולה
                selected = [
                    attractions_by_id[i]
                    for i in ids
                    if i in attractions_by_id
                ]

                if not ids:
                    result = {
                        "valid": False,
                        "error": "לא ניתן לתכנן מסלול ללא אטרקציות."
                    }

                elif (
                    len(selected) != len(ids)
                    or len(ids) != len(set(ids))
                ):
                    result = {
                        "valid": False,
                        "error": (
                            "המסלול מכיל אטרקציות "
                            "לא קיימות או כפולות."
                        )
                    }

                else:
                    result = check_trip(
                        selected,
                        hours,
                        budget
                    )
                    result["attractions"] = selected

                last_validation = result
                weather_result = None

                if result.get("valid"):
                    description = (
                        f"המסלול אושר! "
                        f"משך: {result['total_hours']} שעות, "
                        f"עלות: {result['total_price']} ₪."
                    )

                elif result.get("time_exceeded"):
                    description = (
                        f"המסלול חורג ממגבלת הזמן: "
                        f"{result['total_hours']} שעות "
                        f"במקום {hours} שעות."
                    )

                elif result.get("budget_exceeded"):
                    description = (
                        f"המסלול חורג מהתקציב: "
                        f"{result['total_price']} ₪ "
                        f"במקום {budget} ₪."
                    )

                else:
                    description = result.get(
                        "error",
                        "המסלול אינו תקין."
                    )

                logs.append({
                    "action": "validation",
                    "title": (
                        "המסלול אושר"
                        if result.get("valid")
                        else "נמצאה חריגה במסלול"
                    ),
                    "description": description,
                    "success": result.get("valid", False)
                })

            elif call.name == "get_weather":
                if not (
                    last_validation is not None
                    and last_validation.get("valid") is True
                ):
                    result = {
                        "available": False,
                        "reason": (
                            "יש לאשר מסלול לפני "
                            "בדיקת מזג האוויר."
                        )
                    }

                else:
                    result = get_weather(region, trip_date)
                    weather_result = result

                    if result.get("available"):
                        description = (
                            f"תחזית ל־{trip_date}: "
                            f"{result['temperature_min']}°–"
                            f"{result['temperature_max']}°, "
                            f"סיכוי לגשם: "
                            f"{result['rain_probability']}%."
                        )
                    else:
                        description = result.get(
                            "reason",
                            "תחזית אינה זמינה."
                        )

                    logs.append({
                        "action": "weather",
                        "title": "בדיקת מזג האוויר",
                        "description": description,
                        "success": result.get("available", False)
                    })

            else:
                result = {
                    "valid": False,
                    "error": "Unknown tool"
                }

                last_validation = None
                weather_result = None

                logs.append({
                    "action": "error",
                    "title": "פעולה לא מוכרת",
                    "description": "הסוכן ביקש להפעיל כלי לא מוכר.",
                    "success": False
                })

            # מחזירים למודל את תוצאת הכלי כדי שיוכל להמשיך בתכנון
            messages.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result, ensure_ascii=False)
            })

    return {
        "success": False,
        "result": (
            "הסוכן הגיע למגבלת הפעולות "
            "ולא הצליח להשלים את התכנון."
        ),
        "logs": logs,
        "trip": None,
        "weather": weather_result,
        "equipment": []
    }
