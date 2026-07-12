# 01 — ארכיטקטורה רב-סוכנית

מסמך זה מגדיר את ארכיטקטורת התוכנה של הטייס: שבעה "סוכנים" (agents) בתוך **תהליך Python יחיד**, המתקשרים דרך bus מינימלי, סביב לולאת בקרה חמה אחת ב-250Hz.

"סוכן" כאן הוא יחידת אחריות מובחנת עם ממשק הודעות מוגדר — לא בהכרח thread נפרד. חלק מהסוכנים רצים inline בלולאה החמה; ההפרדה היא לוגית וארכיטקטונית, לא בהכרח תזמונית.

## 1. שבעת הסוכנים + טלמטריה

| # | סוכן | מיקום | תזמון | אחריות |
|---|---|---|---|---|
| 1 | IO | `src/aigp/io/` | 3 threads | קלט/פלט MAVLink, קליטת וידאו, סנכרון זמן, הקלטה גולמית |
| 2 | Perception | `src/aigp/perception/` | thread משלו, בקצב המצלמה | גילוי שער ושחזור pose יחסי-לשער |
| 3 | State Estimation | `src/aigp/estimation/` | inline בלולאה החמה | פילטר attitude + ‏VIO-lite ← ‏`StateEstimate` |
| 4 | Planning | `src/aigp/planning/` | inline, decimated ל-50Hz | התנהגויות המרוץ: search / approach / commit / recover |
| 5 | Flight Control | `src/aigp/control/` | inline ‏250Hz | ‏`ControlBackend` — תרגום פקודת תכנון לפקודת MAVLink |
| 6 | Supervisor | `src/aigp/supervisor/` | inline, ראשון בכל tick | ‏FSM של המרוץ, מדיניות בטיחות, watchdogs, ‏arm/reset |
| 7 | Learning | `src/aigp/learning/` | offline, בין טיסות | לוגים, ניקוד, אופטימייזרים, קמפיינים |
| + | Telemetry | `src/aigp/telemetry/` | thread אסינכרוני | לוגר ניזון מ-tap על ה-bus; ‏plots פוסט-טיסה ב-matplotlib |

### 1.1 IO Agent — `src/aigp/io/`

- `mavlink_io.py` — קליטה ושידור MAVLink (פורט 14550).
- `vision_rx.py` — קליטת UDP בפורט 5600 והרכבת פריימים מ-chunks.
- `timesync.py` — פרוטוקול TIMESYNC ב-10Hz.
- `udp_tap.py` — מקליט גולמי של כל תעבורת ה-UDP; כל טיסה אמיתית מוקלטת אוטומטית.

הקוד מבוסס על ה-template הרשמי של התחרות, עם תיקונים שנדרשו: socket timeouts, ניקוי zombie frames חלקיים (partial-frame GC), טבלת dispatch להודעות במקום שרשרת if, ו-`recv_match` חוסם עם timeout במקום busy-poll. ה-IO Agent מפרסם **הודעות מטופסות** (typed) בלבד — אף צרכן לא נוגע ב-pymavlink objects גולמיים.

### 1.2 Perception Agent — `src/aigp/perception/`

רץ ב-thread משלו, בקצב הגעת הפריימים (לא בקצב הבקרה). מכיל:

- `interface.py` — ‏`GateDetector` ABC, נקודת ההחלפה לגלאי סבב 2 / גלאי נלמד.
- `gate_detector_hsv.py` — גלאי סבב 1 הקלאסי (מסמך [03](03-reiya.md)).
- `camera.py` — מודל pinhole; ה-intrinsics אינם ידועים ולכן ה-FOV מכויל אמפירית וחי ב-`ParamSet`.

הפלט: pose יחסי-לשער דרך `cv2.solvePnP` עם מידות שער נומינליות (רשומת `ParamSet`).

### 1.3 State Estimation — `src/aigp/estimation/`

רץ **inline** בלולאה החמה (לא thread): scalar math זול, ואסור שה-estimate יפגר אחרי הבקרה.

- `attitude_filter.py` — פילטר Mahony/complementary: אינטגרציית gyro עם תיקון כבידה מה-accelerometer.
- `state_estimator.py` — ‏VIO-lite: אינטגרציית תאוצה מפוצת-כבידה למהירות, מרוסנת ומתוקנת על ידי דלתות pose מהראייה.

הפלט הוא `StateEstimate`: attitude quaternion, ‏body rates, מהירות, gate_rel pose + גיל המדידה, ו-health. במפורש **לא** EKF מלא בשלב זה; משבצת השדרוג מבודדת כך שהחלפה עתידית לא נוגעת בשאר המערכת. פירוט במסמך [02](02-bakara-veshichzur-matzav.md).

### 1.4 Planning — `src/aigp/planning/`

Inline, ‏decimated ל-50Hz (התכנון לא צריך 250Hz; הבקרה כן).

- `race_planner.py` — התנהגויות: **search** (סיבוב yaw איטי עד שהגלאי יורה) ← **approach** (יישור לנורמל השער, פרופיל מהירות פרמטרי f(distance)) ← **commit** (חלון עיוור: נעילת וקטור מהירות דרך-השער ל-`commit_duration_s`, אישור דרך אינקרמנט של `active_gate_index`) ← **recover** (אחרי התנגשות/איבוד שער: בלימה ל-hover וחיפוש מחדש).
- `approach.py` — הגיאומטריה.

עיצוב קו-המרוץ פרמטרי לחלוטין — כלומר ניתן לכוונון על ידי לולאת הלמידה.

### 1.5 Flight Control — `src/aigp/control/`

Inline ב-250Hz. ‏`ControlBackend` ABC ב-`interface.py`, ושלושה מימושים על סולם הסמכות:

- `velocity_backend.py` — ברירת המחדל: עיצוב setpoints + מגבלות slew.
- `attitude_rate_backend.py` — שלב 6: שגיאת מהירות ← tilt/thrust ← קסקדת PID של body-rates; ‏`pid.py` עם anti-windup; gains מ-`ParamSet`.
- `motor_backend.py` — stub ל-RPM גולמי בעתיד.

### 1.6 Supervisor — `src/aigp/supervisor/`

- `race_manager.py` — ‏FSM, מתעדכן **ראשון** בכל איטרציה:

```
IDLE → CONNECTING → READY → ARMED → TAKEOFF
     → RACING{search|approach|commit} → FINISHED → RESETTING
ABORT — נגיש מכל מצב
```

- מוזן מ: סטטוס מרוץ, אירועי COLLISION (התנגשות סביבה ב-threat_level 2 ← ‏abort לפי policy; נגיעות בשער נרשמות ונסבלות), ו-watchdogs.
- `watchdog.py` — ‏staleness של IMU מעל 50ms, ‏staleness של פריים מעל 500ms, יחס loop overruns.
- `safety.py` — מדיניות ההתנגשויות.

ה-Supervisor הוא הבעלים הבלעדי של arm ושל reset; מריץ הקמפיינים מדבר רק איתו, לעולם לא ישירות עם ה-IO.

### 1.7 Learning Agent — `src/aigp/learning/`

רץ offline בין טיסות; אינו נוגע בלולאה החמה. ‏`flight_log.py`, ‏`results_db.py`, ‏`metrics.py`, ‏`optimizers.py`, ‏`campaign.py` — פירוט מלא במסמך [04](04-lulaat-lemida.md).

## 2. ה-bus — ‏`src/aigp/core/bus.py`

שני פרימיטיבים בלבד, לפי אופי הזרם:

### 2.1 `LatestValue[T]` — תא חד-ערכי

- `set()` מחליף reference אטומית; `get()` מחזיר `(msg, seq)` כדי שצרכן יזהה טריות (האם seq התקדם מאז הקריאה הקודמת).
- משמש לזרמים בקצב גבוה: IMU, פריימים, detections, ‏state.
- **הסמנטיקה המרכזית**: לולאת הבקרה לעולם לא מחכה ולעולם לא מעבדת backlog — היא צורכת את הערך האחרון בלבד. ערך ישן שנדרס הוא feature, לא bug: בקרה בזמן-אמת רוצה את ההווה, לא את ההיסטוריה.

### 2.2 `EventQueue` — תור חסום-גודל

- ‏`queue.Queue` תחום, לאירועים בדידים שאסור לאבד: COLLISION, שינוי סטטוס מרוץ.
- ה-Supervisor מרוקן אותו **במלואו** בכל tick.

### 2.3 חוזה משותף

- כל publish מציע את ההודעה גם ל-**tap של הלוגר** (drop-with-counter — הלוגר לעולם לא חוסם publisher).
- כל ההודעות הן frozen dataclasses מטופסות ב-`core/messages.py`.

### 2.4 שירותי core נוספים

- `core/clock.py` — ‏`SimClock`: מתחזק `offset = sim_time − client_monotonic` מהודעות TIMESYNC עם median filter ← ציר זמן אחוד ל-IMU, פריימים וזמני מרוץ.
- `core/params.py` — ‏`ParamSet`: ‏flatten/unflatten במפתחות-נקודה (dot-keys) עבור אופטימייזרים, `patch()`, ‏sha256 hash.
- `core/scheduler.py` — ‏`RateLoop`: תזמון absolute-deadline עם מטריקות overrun (מסמך 02).

## 3. מודל התהליכונים — 7 threads

| # | Thread | קצב | תפקיד |
|---|---|---|---|
| 1 | Main — הלולאה החמה | 250Hz | ‏Supervisor tick ← ‏Estimation ← ‏Planning (50Hz) ← ‏Control ← שידור MAVLink |
| 2 | IO: MAVLink RX | לפי הגעה | ‏`recv_match` חוסם עם timeout; פרסום typed messages ל-bus |
| 3 | IO: Vision RX | לפי הגעה | קליטת chunks בפורט 5600, הרכבת JPEG, ‏partial-frame GC |
| 4 | IO: Timesync | 10Hz | שליחת/עיבוד TIMESYNC, עדכון `SimClock` |
| 5 | Perception | קצב מצלמה | ‏decode + ‏detect + ‏PnP; פרסום detection ל-`LatestValue` |
| 6 | Telemetry logger | אסינכרוני | ריקון tap ה-bus לדיסק (JSONL); drop-with-counter |
| 7 | ‏`udp_tap` writer | אסינכרוני | כתיבת ההקלטה הגולמית לדיסק |

### הערת GIL

למה זה עובד תחת ה-GIL של CPython:

- ‏cv2 ו-numpy משחררים את ה-GIL בזמן העבודה הכבדה (decode, ‏contours, ‏solvePnP) — ה-Perception thread לא חונק את הלולאה החמה.
- הנתיב החם עצמו הוא scalar math ללא הקצאות — קצר מספיק לתקציב של **4ms לכל tick**.
- ה-VelocityBackend סובל decimation ל-125Hz אם צריך; ה-AttitudeRateBackend (שלב 6) הוא המקום שבו התזמון באמת קריטי — ושם נמדוד לפני שנתחייב.

## 4. הליכה דרך tick אחד של 250Hz

```
t=0.000ms  RateLoop מעיר את ה-main thread על absolute deadline
t≈0.1ms    Supervisor: ריקון מלא של ה-EventQueue (collision? race status?),
           בדיקת watchdogs, מעבר FSM אם צריך. ראשון תמיד — הבטיחות קודמת.
t≈0.5ms    Estimation: get() על LatestValue של ה-IMU; אם seq התקדם —
           צעד Mahony + צעד VIO-lite. get() על detection; אם טרייה —
           תיקון gate_rel pose. פרסום StateEstimate.
t≈1.5ms    Planning (אחת ל-5 ticks, 50Hz): התנהגות נוכחית מייצרת
           פקודת מהירות/כיוון רצויה מתוך gate_rel pose.
t≈2.0ms    Control: ControlBackend מעצב את הפקודה (slew limits וכו')
           ומייצר הודעת MAVLink.
t≈2.5ms    שידור: set_position_target_local_ned החוצה על UDP.
t≈2.6ms    פרסום מדגמי state/command ל-tap של הלוגר (offer, לא block).
t<4.0ms    סיום; RateLoop ישן עד ה-deadline האבסולוטי הבא ורושם
           מטריקת overrun אם חרגנו.
```

שימו לב מה **לא** קורה ב-tick: אין decode של JPEG (זה ב-Perception thread), אין I/O לדיסק (זה בלוגר), אין parsing של MAVLink (זה ב-RX thread). הלולאה החמה רק קוראת תאים, מחשבת, ומשדרת.

## 5. למה זה עדיף על גישת ה-shared-dict של ה-template

ה-template הרשמי משתף מצב דרך dict גלובלי שכל thread כותב וקורא ממנו. הבעיות, ולמה ה-bus פותר אותן:

| בעיה ב-shared-dict | הפתרון אצלנו |
|---|---|
| אין הבחנה בין "הערך האחרון" ל"כל האירועים" — אירועי collision יכולים להידרס | ‏`LatestValue` לזרמים, `EventQueue` לאירועים בדידים; שום collision לא הולך לאיבוד |
| אין זיהוי טריות — צרכן לא יודע אם הערך חדש או שקרא אותו כבר | ‏`get()` מחזיר `(msg, seq)`; ‏watchdog staleness נבנה על זה ישירות |
| מבני נתונים חופשיים, ללא schema — טעויות מפתח/טיפוס מתגלות בטיסה | frozen dataclasses ב-`core/messages.py`; טעות מתגלה מיד וב-type checker |
| כתיבה/קריאה לא ממושמעת יוצרת race conditions עדינים | החלפת reference אטומית ב-`LatestValue`; אין mutation של הודעה שפורסמה (frozen) |
| אין נקודת האזנה אחידה ללוגינג — לוגים מפוזרים ולא שלמים | כל publish עובר דרך tap אחד; הקלטה מלאה כמעט בחינם |
| הלוגינג עלול לחסום את המפרסם | ‏drop-with-counter: הלוגר מפיל ומונה, לעולם לא חוסם |

## 6. עץ המאגר

```
eni_dcim/
├── docs/                        # המסמכים האלה
├── src/aigp/
│   ├── core/
│   │   ├── bus.py               # LatestValue, EventQueue, logger tap
│   │   ├── messages.py          # frozen dataclasses מטופסות
│   │   ├── clock.py             # SimClock (TIMESYNC + median filter)
│   │   ├── params.py            # ParamSet: flatten/patch/sha256
│   │   └── scheduler.py         # RateLoop — absolute-deadline
│   ├── io/
│   │   ├── mavlink_io.py        # MAVLink RX/TX, פורט 14550
│   │   ├── vision_rx.py         # UDP 5600, הרכבת chunks
│   │   ├── timesync.py          # פרוטוקול TIMESYNC 10Hz
│   │   └── udp_tap.py           # הקלטה גולמית אוטומטית
│   ├── perception/
│   │   ├── interface.py         # GateDetector ABC
│   │   ├── gate_detector_hsv.py # גלאי סבב 1
│   │   └── camera.py            # מודל pinhole, FOV מ-ParamSet
│   ├── estimation/
│   │   ├── attitude_filter.py   # Mahony/complementary
│   │   └── state_estimator.py   # VIO-lite → StateEstimate
│   ├── planning/
│   │   ├── race_planner.py      # search/approach/commit/recover
│   │   └── approach.py          # גיאומטריית הגישה
│   ├── control/
│   │   ├── interface.py         # ControlBackend ABC
│   │   ├── velocity_backend.py  # ברירת מחדל
│   │   ├── attitude_rate_backend.py  # שלב 6
│   │   ├── motor_backend.py     # stub עתידי
│   │   └── pid.py               # PID עם anti-windup
│   ├── supervisor/
│   │   ├── race_manager.py      # ה-FSM
│   │   ├── watchdog.py          # staleness + overruns
│   │   └── safety.py            # מדיניות התנגשויות
│   ├── learning/
│   │   ├── flight_log.py        # JSONL פר טיסה
│   │   ├── results_db.py        # SQLite
│   │   ├── metrics.py           # פונקציית הניקוד
│   │   ├── optimizers.py        # RandomSearch/CEM/CMA-ES
│   │   └── campaign.py          # לולאת ask→fly→tell
│   └── telemetry/               # לוגר אסינכרוני + plots
├── simtools/
│   ├── mock_sim.py              # סימולטור קינמטי (מסמך 06)
│   ├── record.py                # מקליט/מעביר UDP (רץ על Windows)
│   └── replay_server.py         # שידור-חוזר של הקלטות בתזמון מקורי
├── scripts/
│   ├── fly_once.py              # טיסה בודדת מול הסים האמיתי
│   └── frame_probe.py           # ניסוי NED-vs-BODY (מסמך 02)
└── tests/                       # unit + integration (מסמך 06)
```

## 7. עקרונות חתך-רוחב

1. **תלות חד-כיוונית**: ‏agents תלויים ב-`core/`, לא זה בזה; התקשורת רק דרך ה-bus.
2. **נקודות החלפה מפורשות**: ‏`GateDetector` ו-`ControlBackend` הם ה-seams היחידים שסבב 2 ולמידה עתידית נוגעים בהם.
3. **הפרדת מהיר/איטי**: כל מה שב-250Hz — inline ו-allocation-free; כל השאר — threads שמזינים `LatestValue`.
4. **הכל דרך ה-Supervisor**: אף רכיב חוץ ממנו לא שולח arm/reset; מריץ הקמפיינים הוא לקוח שלו בלבד.
