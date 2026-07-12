# 04 — לולאת הלמידה מטיסה לטיסה

"שיפור מטיסה לטיסה" הוא דרישת ליבה של התחרות. אצלנו זו לא הבטחת RL עמומה אלא מנגנון קונקרטי: כל פרמטר הוא דאטה, כל טיסה נמדדת ונרשמת, ואופטימייזר קופסה-שחורה סוגר את הלולאה דרך איפוס אוטומטי של הסימולטור (פקודת MAVLink ‏31000). מסמך זה מפרט את המנגנון, ב-`src/aigp/learning/` וב-`core/params.py`.

## 1. ‏ParamSet — פרמטרים כדאטה (`src/aigp/core/params.py`)

- **כל** ערך כוונון במערכת — ספי גלאי, פרופילי מהירות, מרחקי commit, ‏slew limits, ‏gains של PID, ‏FOV, מידות שער — חי ב-`ParamSet` אחד, נשמר כ-JSON ממוגרס.
- ‏API:
  - `flatten()` / `unflatten()` — מיפוי למפתחות-נקודה (dot-keys), למשל `planner.approach.v_max`. זה הממשק לאופטימייזרים: וקטור ערכים שטוח עם שמות יציבים.
  - `patch(overrides)` — החלת תת-קבוצה של מפתחות (מה שהאופטימייזר מציע) על בסיס נתון.
  - ‏sha256 hash על הייצוג הקנוני — זהות פרמטרים חד-ערכית.
- **צילום-מצב פר טיסה**: כל טיסה נפתחת בכתיבת ה-ParamSet המלא + ה-hash שלו ללוג ולמסד. אין טיסה "עם פרמטרים לא ידועים" — זו הדרישה המינימלית לשחזוריות ולכל אופטימיזציה.

## 2. תיעוד טיסות

### 2.1 לוג טיסה — `flight_log.py`

קובץ JSONL אחד פר טיסה: שורת header (זהות טיסה, param_hash, params מלאים, גרסת קוד), ואחריה רשומות מוחתמות-זמן — ‏StateEstimate מדוגם, פקודות בקרה, ‏detections, אירועי FSM, ‏collisions, סטטוס מרוץ, מטריקות RateLoop. נכתב על ידי ה-telemetry thread (‏drop-with-counter — הלוג לעולם לא מאט את הטיסה). לצידו: הקלטת ה-UDP הגולמית מ-`io/udp_tap.py`.

### 2.2 מסד התוצאות — `results_db.py` (SQLite)

```sql
CREATE TABLE flights (
    flight_id     TEXT PRIMARY KEY,
    campaign_id   TEXT REFERENCES campaigns(campaign_id),
    started_at    TEXT NOT NULL,          -- ISO-8601
    param_hash    TEXT NOT NULL,          -- sha256 של ה-ParamSet
    params_json   TEXT NOT NULL,          -- הצילום המלא
    gates_passed  INTEGER NOT NULL,
    lap_time_s    REAL,                   -- NULL אם ההקפה לא הושלמה
    collisions    INTEGER NOT NULL,
    aborted       INTEGER NOT NULL,       -- boolean
    score         REAL NOT NULL,
    log_path      TEXT                    -- הפניה ל-JSONL
);

CREATE TABLE campaigns (
    campaign_id   TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    optimizer     TEXT NOT NULL,          -- "random" | "cem" | "cma-es"
    tuned_keys    TEXT NOT NULL,          -- JSON: רשימת dot-keys
    base_params   TEXT NOT NULL,          -- ParamSet הבסיס
    notes         TEXT
);
```

‏SQLite ולא קבצים: שאילתות ("הטיסה הטובה ביותר בקמפיין X", "כל הטיסות עם param_hash Y") הן שורת SQL; המסד הוא artifact יחיד שמעתיקים מה-Windows חזרה למאגר; ושחזור מלא — `params_json` + הלוג — נשלף ממנו ישירות.

## 3. פונקציית הניקוד — `metrics.py`

```
score = gates_passed * W − lap_time − collision_penalty − abort_penalty
```

הרציונל, איבר-איבר:

| איבר | תפקיד | הערות |
|---|---|---|
| `gates_passed * W` | האות הראשי; מדורג, לא בינארי | ‏`active_gate_index` הוא המקור — האורקל היחיד וגם ה-reward. ‏W גדול מספיק כדי ששער נוסף תמיד ינצח שיפור זמן — קודם משלימים, אחר כך מאיצים |
| `− lap_time` | מהירות | נכנס אפקטיבית רק כשההקפה מושלמת; בהקפות חלקיות ההפרש בשערים דומיננטי |
| `− collision_penalty` | עונש התנגשות | סביבה (id 1002) ביוקר; נגיעת שער (id 1001) בזול או אפס — נגיעות שער נסבלות במדיניות |
| `− abort_penalty` | ‏aborts אינם "בחינם" | בלי זה האופטימייזר לומד שפרמטרים שמפילים watchdog מוקדם זולים |

עיצוב מדורג בכוונה: פונקציה בינארית ("הקפה או כלום") מרעיבה את האופטימייזר בשלבים המוקדמים, כשרוב הטיסות חלקיות. שיפוע דרך `gates_passed` נותן כיוון גם כשאף קונפיגורציה לא משלימה הקפה. המשקלים עצמם — רשומות `ParamSet` (לא מכווננים בתוך קמפיין, אבל ממוגרסים ומתועדים פר קמפיין).

## 4. סולם האופטימייזרים — `optimizers.py`

הכל numpy-only, מאחורי ABC אחיד בסגנון ask/tell:

```python
class Optimizer(ABC):
    def ask(self) -> dict[str, float]: ...   # הצעת overrides על dot-keys
    def tell(self, params: dict[str, float], score: float) -> None: ...
```

| שלב | אלגוריתם | מתי ולמה |
|---|---|---|
| 1 | RandomSearch | ‏baseline + חקירת טווחים; חושף באגים בצנרת הקמפיין לפני שמכניסים אלגוריתם "חכם"; baseline ש-CEM חייב לנצח |
| 2 | CEM (Cross-Entropy Method) | אליטיזם על גאוסיאן: דוגמים אוכלוסייה, מתאימים ממוצע/שונות לאחוזון העליון. ~30 שורות, חסין רעש, טוב ב-6–10 ממדים |
| 3 | CMA-ES קומפקטי | מוסיף אדפטציית קווריאנס מלאה — לוכד קורלציות בין פרמטרים (מהירות גישה ↔ מרחק commit). מימוש קומפקטי, נשאר numpy-only |

**למה לא RL עכשיו**:

- תקציב הדגימות: צעד RL דורש אלפי–מיליוני אינטראקציות; אצלנו "דגימה" היא טיסה שלמה (עשרות שניות + reset). קופסה-שחורה על 6–10 פרמטרים מפיקה שיפור מדיד תוך עשרות טיסות — ‏Phase 5 דורש בדיוק את זה (שיפור ≥15% בקמפיין של ≥20 טיסות).
- המבנה כבר קיים: ה-planner וה-backends מקודדים ידע דומייני; ‏RL היה צריך ללמוד אותו מאפס, כולל את כל מצבי הכשל.
- שחזוריות ובטיחות: וקטור פרמטרים ניתן לביקורת ולשחזור מהמסד; policy נלמדת — הרבה פחות.

**ה-hook ל-RL בעתיד** (מתוכנן, לא מאולתר): ‏(א) ה-`Optimizer` ABC הוא הממשק שרכיב policy-learning עתידי מתחבר אליו; (ב) רשומות `(params, log, score)` פר טיסה — כולל לוגי ה-JSONL המלאים — הן הדאטהסט שהוא יצרוך; (ג) ‏`ControlBackend` הוא ה-seam לבקר נלמד: policy שעומדת בחוזה הממשק נכנסת בלי לגעת בשאר המערכת.

## 5. לולאת הקמפיין — `campaign.py`

```
                 ┌────────────────────────────────────────────┐
                 │                 Campaign loop               │
                 └────────────────────────────────────────────┘
    ┌──────────┐   overrides    ┌──────────────────┐
    │ Optimizer│ ──── ask() ──► │ ParamSet.patch() │
    └────▲─────┘                └────────┬─────────┘
         │                               ▼
         │                      ┌──────────────────┐
         │                      │ sim reset         │  MAVLink cmd 31000
         │                      │ (דרך ה-Supervisor)│
         │                      └────────┬─────────┘
         │                               ▼
         │                      ┌──────────────────┐
         │                      │ fly (FSM מלא:     │  IDLE→…→RACING→
         │                      │ arm→takeoff→race) │  FINISHED/ABORT
         │                      └────────┬─────────┘
         │                               ▼
         │                      ┌──────────────────┐
         │       score          │ score (metrics)   │ ◄─ gates, זמן, collisions
         └────── tell() ─────── │ + record (SQLite  │
                                │   + JSONL + tap)  │
                                └──────────────────┘
```

כללי הריצה:

- מריץ הקמפיין מדבר **רק עם ה-Supervisor** (הבעלים של arm/reset) — לא עם ה-IO ישירות.
- טיסה נחשבת גם כשנכשלה: ‏abort, ‏timeout או התרסקות מקבלים score (עם העונשים) ונרשמים — כישלונות הם דאטה.
- ‏timeout פר טיסה + retry על reset שלא נתפס, כדי שקמפיין לילה לא ייתקע על טיסה אחת.
- הקמפיין כולו רץ end-to-end גם מול `simtools/mock_sim.py` — כך ה-CI מוודא את הצנרת (‏ask→patch→reset→fly→score→tell) בלי הסימולטור האמיתי; מול הסים האמיתי רק ה"פיזיקה" משתנה.

## 6. אילו פרמטרים מכווננים קודם

מתחילים צר — ‏6–10 מפתחות עם השפעה ישירה על ה-score ופרשנות פיזיקלית ברורה:

| ‏dot-key (מייצג) | תחום | למה הוא ברשימה הראשונה |
|---|---|---|
| `planner.approach.v_max` | תכנון | המהירות בציר המרוץ — ה-tradeoff המרכזי זמן/בטיחות |
| `planner.approach.speed_profile_gain` | תכנון | צורת f(distance) — כמה מוקדם מאטים לפני שער |
| `planner.commit.distance` | תכנון | מתי נועלים וקטור — קריטי לחלון העיוור |
| `planner.commit.duration_s` | תכנון | אורך הטיסה העיוורת — קריטי בטיחותית (מסמך 02) |
| `control.velocity.slew_limit` | בקרה | חדות תגובה מול overshoot |
| `perception.hsv.threshold_lo/hi` | ראייה | ‏detection rate — קובע כמה זמן טסים עיוור |
| `planner.search.yaw_rate` | תכנון | מהירות ההתאוששות אחרי איבוד שער |

‏gains של קסקדת ה-PID מצטרפים ב-Phase 6, כשה-AttitudeRateBackend נכנס — אותו מנגנון קמפיין בדיוק, מפתחות אחרים.

## 7. שחזוריות — הדרישות המחייבות

1. כל טיסה: ‏param_hash + ‏params_json מלא במסד — תמיד.
2. ‏seed של האופטימייזר נרשם ברשומת הקמפיין.
3. קריטריון הקבלה של Phase 5 כולל במפורש: התוצאה **ניתנת לשחזור מה-DB** — שליפת הפרמטרים הטובים ביותר והרצתם מחדש משיגה ביצועים דומים.
4. לוגי ה-JSONL וההקלטות הגולמיות נשמרים לצד המסד; טיסת-שיא חריגה ניתנת לנתיחה פריים-אחר-פריים ולהפיכה ל-fixture רגרסיה (מסמך [06](06-bdikot-veshichzur.md)).
