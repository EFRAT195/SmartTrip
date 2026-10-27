
import { useEffect, useState } from "react";
import { getAttractionImage } from "./imageService";
import "./App.scss";

// מבנה הנתונים של אטרקציה שמתקבלת מהשרת
type Attraction = {
  id: number;
  name: string;
  duration: number;
  price: number;
};

type AgentLog = {
  action: string;
  title: string;
  description: string;
  success: boolean;
};

type Weather = {
  available: boolean;
  region?: string;
  date?: string;
  temperature_max?: number;
  temperature_min?: number;
  rain_probability?: number;
  weather_code?: number;
  reason?: string;
};

type EquipmentItem = {
  name: string;
  reason: string;
};

// מבנה התשובה המלאה שהשרת מחזיר
type TripResponse = {
  success: boolean;
  result: string;
  logs: AgentLog[];
  trip_date: string;
  weather: Weather | null;
  equipment: EquipmentItem[];
  trip: {
    valid: boolean;
    total_hours: number;
    total_price: number;
    attractions: Attraction[];
  } | null;
};

const categories = [
  { value: "טבע", label: "טבע ונופים" },
  { value: "משפחה", label: "משפחתי" },
  { value: "תרבות", label: "תרבות ומוזיאונים" },
  { value: "היסטוריה", label: "היסטוריה ומורשת" },
  { value: "מעיינות", label: "מעיינות ונחלים" },
  { value: "מסלולי הליכה", label: "מסלולי הליכה" },
  { value: "תצפיות", label: "תצפיות ונופים" },
  { value: "פארקים", label: "פארקים וגנים" },
  { value: "זוגי", label: "טיול זוגי" },
  { value: "חופים", label: "חופים וים" },
];

// יצירת תאריך מקומי בפורמט שמתאים לשדה date
function getLocalDate() {
  const now = new Date();

  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

// רכיב נפרד לכל אטרקציה, כולל חיפוש תמונה מהאינטרנט
function AttractionCard({
  attraction,
  index,
}: {
  attraction: Attraction;
  index: number;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(true);

  useEffect(() => {
    let active = true;

    setImageLoading(true);
    setImageUrl(null);

    getAttractionImage(attraction.name).then((url) => {
      if (active) {
        setImageUrl(url);
        setImageLoading(false);
      }
    });

    return () => {
      active = false;
    };
  }, [attraction.name]);

  return (
    <div className="attraction-item">
      <div className="attraction-image">
        {imageLoading ? (
          <div className="image-placeholder">
            מחפש תמונה...
          </div>
        ) : imageUrl ? (
          <img
            src={imageUrl}
            alt={attraction.name}
            loading="lazy"
            onError={() => setImageUrl(null)}
          />
        ) : (
          <div className="image-placeholder">🏞️</div>
        )}
      </div>

      <div className="attraction-content">
        <span className="attraction-number">
          תחנה {index + 1}
        </span>

        <h3>{attraction.name}</h3>

        <p>
          ⏱ {attraction.duration} שעות
          {" · "}
          💰 {attraction.price} ₪
        </p>
      </div>
    </div>
  );
}

// הצגת התחזית שהתקבלה מכלי מזג האוויר של הסוכן
function WeatherCard({ weather }: { weather: Weather | null }) {
  return (
    <section className="weather-card">
      <div className="info-card-heading">
        <span className="info-card-icon">🌤️</span>

        <div>
          <h3>מזג האוויר ביום הטיול</h3>
          <p>תחזית שהתקבלה משירות מזג אוויר חיצוני</p>
        </div>
      </div>

      {weather?.available ? (
        <div className="weather-stats">
          <div className="weather-stat">
            <span>טמפרטורה מקסימלית</span>
            <strong>{weather.temperature_max}°</strong>
          </div>

          <div className="weather-stat">
            <span>טמפרטורה מינימלית</span>
            <strong>{weather.temperature_min}°</strong>
          </div>

          <div className="weather-stat">
            <span>סיכוי לגשם</span>
            <strong>{weather.rain_probability}%</strong>
          </div>
        </div>
      ) : (
        <p className="weather-unavailable">
          {weather?.reason ??
            "לא זמינה תחזית לתאריך שנבחר."}
        </p>
      )}
    </section>
  );
}

// כל פריט ציוד מוצג עם הסיבה שהסוכן נתן להמלצה
function EquipmentCard({
  equipment,
}: {
  equipment: EquipmentItem[];
}) {
  return (
    <section className="equipment-card">
      <div className="info-card-heading">
        <span className="info-card-icon">🎒</span>

        <div>
          <h3>מה כדאי להביא לטיול?</h3>
          <p>המלצות שהסוכן התאים למסלול שלך</p>
        </div>
      </div>

      {equipment.length > 0 ? (
        <div className="equipment-list">
          {equipment.map((item, index) => (
            <div className="equipment-item" key={index}>
              <span className="equipment-check">✓</span>

              <div className="equipment-content">
                <strong>{item.name}</strong>
                <p>{item.reason}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="equipment-empty">
          לא התקבלו המלצות ציוד למסלול הזה.
        </p>
      )}
    </section>
  );
}

function App() {
  const [region, setRegion] = useState("ירושלים");
  const [category, setCategory] = useState("טבע");
  const [hours, setHours] = useState(4);
  const [budget, setBudget] = useState(100);
  const [tripDate, setTripDate] = useState(getLocalDate);

  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // שליחת העדפות המשתמש לסוכן וקבלת המסלול וההמלצות
  async function planTrip() {
    setLoading(true);
    setError("");
    setTrip(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:64161/plan-trip",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            region,
            category,
            hours,
            budget,
            trip_date: tripDate,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("שגיאה בתכנון הטיול");
      }

      const data: TripResponse = await response.json();

      setTrip(data);
    } catch {
      setError(
        "לא הצלחנו לתכנן את הטיול. ודאי ששרת FastAPI פועל."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app" dir="rtl">
      <header className="header">
        <div className="logo">✈ SmartTrip</div>
        <span className="header-tag">AI Travel Agent</span>
      </header>

      <main className="container">
        
<section className="hero">
  {/* אלמנטים דקורטיביים ברקע */}
  <div className="hero-glow hero-glow-one" />
  <div className="hero-glow hero-glow-two" />

  <div className="hero-content">
    <span className="hero-badge">
      <span className="hero-badge-dot" />
      הכירי את SmartTrip AI
    </span>

    <h1>
      הטיול הבא שלך,
      <br />
      <span>מתוכנן חכם.</span>
    </h1>

    <p>
      פחות זמן על חיפושים, יותר זמן לחוויות.
      <br />
      הסוכן החכם שלנו בונה עבורך מסלול אישי,
      בודק מגבלות ומתאים המלצות למזג האוויר.
    </p>

    <div className="hero-features">
      <span>✦ בחירת אטרקציות חכמה</span>
      <span>✓ בדיקת זמן ותקציב</span>
      <span>☀ התאמה למזג האוויר</span>
    </div>
  </div>
</section>


        <section className="planner-card">
          <div className="section-heading">
            <div>
              <h2>בואי נתכנן את הטיול שלך</h2>
              <p>מלאי כמה פרטים והסוכן יתחיל לעבוד</p>
            </div>

            <span className="section-icon">🗺️</span>
          </div>

          <div className="form-grid">
            <label>
              אזור הטיול

              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              >
                <option value="ירושלים">
                  ירושלים והסביבה
                </option>
                <option value="צפון">צפון</option>
                <option value="מרכז">מרכז</option>
              </select>
            </label>

            <label>
              סוג הטיול

              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {categories.map((item) => (
                  <option
                    key={item.value}
                    value={item.value}
                  >
                    {item.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              כמה שעות יש לך?

              <input
                type="number"
                min="0.5"
                step="0.5"
                value={hours}
                onChange={(e) =>
                  setHours(Number(e.target.value))
                }
              />
            </label>

            <label>
              תקציב מקסימלי (₪)

              <input
                type="number"
                min="0"
                value={budget}
                onChange={(e) =>
                  setBudget(Number(e.target.value))
                }
              />
            </label>

            <label>
              מתי מתוכנן הטיול?

              <input
                type="date"
                min={getLocalDate()}
                value={tripDate}
                onChange={(e) =>
                  setTripDate(e.target.value)
                }
              />
            </label>
          </div>

          <button
            className="plan-button"
            onClick={planTrip}
            disabled={
              loading ||
              hours <= 0 ||
              budget < 0 ||
              !tripDate
            }
          >
            {loading
              ? "הסוכן מתכנן את הטיול..."
              : "✨ תכנני לי טיול"}
          </button>

          {error && <p className="error">{error}</p>}
        </section>

        {loading && (
          <div className="loading-card">
            <div className="spinner" />

            <h3>הסוכן שלנו עובד בשבילך</h3>

            <p>
              מחפש אטרקציות, בודק מגבלות,
              בודק מזג אוויר ומתאים ציוד...
            </p>
          </div>
        )}

        {trip && (
          <div className="results">
            <section className="result-card">
              <span className="eyebrow">
                {trip.success
                  ? "המסלול שלך מוכן"
                  : "לא ניתן להשלים את התכנון"}
              </span>

              <h2>
                {trip.success
                  ? "🌿 הטיול שהסוכן תכנן"
                  : "🔎 לא נמצא מסלול מתאים"}
              </h2>

              {trip.success && trip.trip ? (
                <>
                  <div className="trip-summary-grid">
                    <div className="summary-item">
                      <strong>📅 תאריך הטיול</strong>

                      <p>
                        {new Date(
                          `${trip.trip_date}T12:00:00`
                        ).toLocaleDateString("he-IL")}
                      </p>
                    </div>

                    <div className="summary-item">
                      <strong>⏱ זמן כולל</strong>
                      <p>
                        {trip.trip.total_hours} שעות
                      </p>
                    </div>

                    <div className="summary-item">
                      <strong>💰 עלות כוללת</strong>
                      <p>
                        {trip.trip.total_price} ₪
                      </p>
                    </div>
                  </div>

                  <h3>האטרקציות במסלול</h3>

                  <div className="attractions-list">
                    {trip.trip.attractions.map(
                      (attraction, index) => (
                        <AttractionCard
                          key={attraction.id}
                          attraction={attraction}
                          index={index}
                        />
                      )
                    )}
                  </div>

                  {/* התחזית והציוד מוצגים רק אחרי שהמסלול אושר */}
                  <div className="trip-advice">
                    <WeatherCard
                      weather={trip.weather ?? null}
                    />

                    <EquipmentCard
                      equipment={trip.equipment ?? []}
                    />
                  </div>

                  {trip.result && (
                    <div className="trip-text">
                      {trip.result}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p>
                    לא נמצאו אטרקציות שעומדות בכל
                    המגבלות שהגדרת. אפשר לשנות את
                    התקציב, הזמן או סוג הטיול ולנסות שוב.
                  </p>

                  <div className="trip-text">
                    {trip.result}
                  </div>
                </>
              )}
            </section>

            <section className="agent-card">
              <div className="agent-heading">
                <span className="agent-icon">🧠</span>

                <div>
                  <h2>מאחורי הקלעים</h2>

                  <p>
                    כך הסוכן קיבל החלטות באופן עצמאי
                  </p>
                </div>
              </div>

              {/* יומן הפעולות מאפשר לראות את החלטות הסוכן */}
              <div className="steps">
                {trip.logs.map((log, index) => (
                  <div className={`step ${log.success ? "step-success" : "step-warning"}`} key={index}>
                    <span className="step-number">
                      {index + 1}
                    </span>

                    <div>
                      <strong>
                        {log.success ? "✓ " : "⚠ "}
                        {log.title}
                      </strong>

                      <p>{log.description}</p>
                    </div>
                  </div>
                ))}
              </div>

              <details className="technical-logs">
                <summary>
                  הצגת יומן פעולות טכני
                </summary>

                {trip.logs.map((log, index) => (
                  <pre key={index}>
                    {JSON.stringify(log, null, 2)}
                  </pre>
                ))}
              </details>
            </section>
          </div>
        )}
      </main>

      <footer>
        SmartTrip © 2026 · Powered by AI
        <span>תכנון חכם. החלטות עצמאיות.</span>
      </footer>
    </div>
  );
}

export default App;
