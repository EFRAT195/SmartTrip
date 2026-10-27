import json
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from tools import search_attractions, check_trip
from weather_tool import get_weather

load_dotenv()
client = OpenAI(timeout=35.0, max_retries=1)


def safe_openai_response(**kwargs):
    """Return an OpenAI response or a controlled error message."""
    try:
        return client.responses.create(**kwargs), None
    except OpenAIError:
        return None, "שירות הבינה המלאכותית אינו זמין כרגע. נסי שוב מאוחר יותר."
    except (TimeoutError, ConnectionError):
        return None, "הבקשה לשירות הבינה המלאכותית נכשלה עקב בעיית תקשורת."


def failure_response(message, logs, weather=None):
    return {
        "success": False,
        "result": message,
        "selection_reason": "",
        "logs": logs,
        "trip": None,
        "weather": weather,
        "equipment": []
    }


def parse_json_object(raw):
    """Reject malformed JSON and JSON values other than objects."""
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


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
            "selection_reason": {
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
        "required": ["summary", "selection_reason", "equipment"],
        "additionalProperties": False
    }
}


def run_agent(region, category, hours, budget, trip_date):
    attractions_by_id = {}
    last_validation = None
    last_attempt_ids = None
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
        response, api_error = safe_openai_response(
            model="gpt-4o-mini",
            instructions=instructions,
            input=messages,
            tools=TOOLS
        )
        if api_error:
            logs.append({
                "action": "error", "title": "שגיאה בשירות AI",
                "description": api_error, "success": False
            })
            return failure_response(api_error, logs, weather_result)

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
            final_response, api_error = safe_openai_response(
                model="gpt-4o-mini",
                instructions=(
                    instructions
                    + """

Return a JSON object:
- summary: a short Hebrew explanation of the trip
  and weather, or why planning failed.
- selection_reason: a short Hebrew explanation of why the selected
  attractions fit the user's preferences, time and budget.
  Base it only on actual search and validation results.
  Do not invent reasons for excluding other attractions.
  If no trip was validated, return an empty string.
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

            if api_error:
                logs.append({
                    "action": "error", "title": "שגיאה בהפקת ההמלצות",
                    "description": api_error, "success": False
                })
                return failure_response(api_error, logs, weather_result)

            # מוודאים שהפלט תקין לפני שניגשים לשדות שלו.
            recommendations = parse_json_object(final_response.output_text)
            if (
                recommendations is None
                or not isinstance(recommendations.get("summary"), str)
                or not isinstance(recommendations.get("selection_reason"), str)
                or not isinstance(recommendations.get("equipment"), list)
                or any(
                    not isinstance(item, dict)
                    or not isinstance(item.get("name"), str)
                    or not isinstance(item.get("reason"), str)
                    for item in recommendations.get("equipment", [])
                )
            ):
                message = "התקבלה תשובה לא תקינה מהמודל. נסי שוב."
                logs.append({
                    "action": "error", "title": "תשובת AI לא תקינה",
                    "description": message, "success": False
                })
                return failure_response(message, logs, weather_result)

            equipment = (
                recommendations["equipment"]
                if success
                else []
            )

            # נימוק הבחירה מבוסס על המסלול שאושר, ולא על השערות
            selection_reason = (
                recommendations["selection_reason"].strip()
                if success
                else ""
            )

            # משלבים את הנימוק בטקסט הקיים כדי שיופיע בממשק ללא שינוי ב-React
            final_summary = recommendations["summary"]
            if selection_reason:
                final_summary += "\n\nלמה נבחר המסלול? " + selection_reason

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
                "result": final_summary,
                "selection_reason": selection_reason,
                "logs": logs,
                "trip": last_validation if success else None,
                "weather": weather_result,
                "equipment": equipment
            }

        # מפעילים בפועל את הכלי שהמודל ביקש
        for call in calls:
            args = parse_json_object(call.arguments)
            if args is None:
                result = {"valid": False, "error": "התקבלו ארגומנטים לא תקינים מהמודל."}
                logs.append({
                    "action": "error", "title": "ארגומנטים לא תקינים",
                    "description": result["error"], "success": False
                })
                messages.append({
                    "type": "function_call_output", "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False)
                })
                continue

            if call.name == "search_attractions":
                result = search_attractions(region, category)

                attractions_by_id = {
                    attraction["id"]: attraction
                    for attraction in result
                }

                last_validation = None
                last_attempt_ids = None
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
                ids = args.get("attraction_ids")
                if (
                    not isinstance(ids, list)
                    or any(type(item) is not int for item in ids)
                ):
                    ids = []

                # מציגים ניסיון תיקון רק אם הבדיקה הקודמת נכשלה
                # והמודל בחר הפעם הרכב אטרקציות שונה
                if (
                    last_validation is not None
                    and not last_validation.get("valid", False)
                    and last_attempt_ids is not None
                    and ids != last_attempt_ids
                ):
                    logs.append({
                        "action": "revision",
                        "title": "הסוכן שינה את המסלול",
                        "description": (
                            "בעקבות הבדיקה שנכשלה, הסוכן בחר "
                            "הרכב אטרקציות אחר ושלח אותו לבדיקה חוזרת."
                        ),
                        "success": True
                    })

                last_attempt_ids = list(ids)

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
                    try:
                        result = get_weather(region, trip_date)
                        if not isinstance(result, dict):
                            raise ValueError("Invalid weather response")
                    except Exception:
                        # כשל בשירות חיצוני לא מבטל מסלול שכבר אושר.
                        result = {
                            "available": False,
                            "reason": "לא ניתן לקבל כרגע תחזית מזג אוויר."
                        }
                    weather_result = result

                    if result.get("available") and all(
                        key in result
                        for key in ("temperature_min", "temperature_max", "rain_probability")
                    ):
                        description = (
                            f"תחזית ל־{trip_date}: "
                            f"{result['temperature_min']}°–"
                            f"{result['temperature_max']}°, "
                            f"סיכוי לגשם: "
                            f"{result['rain_probability']}%."
                        )
                    else:
                        result = {
                            "available": False,
                            "reason": result.get("reason") or "תחזית אינה זמינה."
                        }
                        weather_result = result
                        description = result["reason"]

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
        "selection_reason": "",
        "logs": logs,
        "trip": None,
        "weather": weather_result,
        "equipment": []
    }
