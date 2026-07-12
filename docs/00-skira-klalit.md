# 00 — סקירה כללית

מסמך זה הוא נקודת הכניסה לסט מסמכי התכנון של טייס ה-AI האוטונומי שלנו לתחרות ה-AI Grand Prix (AI-GP). המערכת ממומשת ב-Python במאגר זה, בחבילת `aigp` בפריסת src (`src/aigp/`).

## 1. התחרות

AI-GP היא תחרות מרוצי רחפנים אוטונומיים בחסות Anduril, DCL (Drone Champions League) ו-Neros. עיקרי התחרות:

- **הפלטפורמה**: quadcopter (4 מנועים) שטס דרך רצף של שערים (gates) על מסלול מרוץ.
- **אוטונומיה מלאה**: אפס התערבות אנושית מרגע הזינוק. הטייס הוא תוכנה בלבד.
- **ללא GPS**: אין מיקום מוחלט, אין קואורדינטות גלובליות. שחזור המצב חייב להיות עצמאי לחלוטין — IMU ומצלמת FPV בלבד.
- **הסימולטור**: `FlightSim.exe`, אפליקציית Windows מבוססת Unreal. הלקוח שלנו הוא תהליך Python שמתקשר איתו על גבי UDP.
- **סבב 1 (Round 1)**: סביבה פשוטה, desaturated, עם שערים בניגודיות גבוהה — מותאמת לגילוי קלאסי.
- **סבב 2 (Round 2)**: סביבות high-fidelity שנסרקו תלת-ממדית (3D-scanned) — דורש גלאי חזק יותר.
- **לוח זמנים**: מוקדמות פיזיות בספטמבר 2026, גמר בנובמבר 2026.

## 2. ממשק הסימולטור — עובדות מחייבות

### 2.1 בקרה (client → sim)

הלקוח שולח פקודות בקצב **250Hz** על MAVLink מעל UDP בפורט **14550**. שלושה מצבי בקרה זמינים:

| # | הודעת MAVLink | משמעות | רמת סיכון/שליטה |
|---|---|---|---|
| 1 | `set_actuator_control_target` | RPM ישיר לארבעת המנועים `[FL, FR, BL, BR]` | שליטה מלאה, אפס ייצוב פנימי |
| 2 | `set_attitude_target` | body rates ‏[rad/s] + collective thrust בטווח 0..1 | ייצוב זווית עלינו |
| 3 | `set_position_target_local_ned` | velocity setpoints — לסימולטור יש בקר טיסה פנימי | הכי בטוח; הסימולטור מייצב attitude |

אסטרטגיית "סולם סמכות הבקרה" (מתחילים ממצב 3, מטפסים) מפורטת במסמך [02](02-bakara-veshichzur-matzav.md).

### 2.2 טלמטריה (sim → client)

| הודעה | תוכן | הערות |
|---|---|---|
| `HEARTBEAT` | חיוּת החיבור | |
| `TIMESYNC` | פרוטוקול סנכרון שעונים ב-10Hz | בסיס ל-`SimClock` |
| `HIGHRES_IMU` | accel + gyro | חיישן המצב היחיד מלבד המצלמה |
| `ACTUATOR_OUTPUT_STATUS` | מצב המנועים בפועל | |
| `COLLISION` | ‏id=1001 שער, id=1002 סביבה; `threat_level` 1–2; עוצמת impulse | מזין את מדיניות הבטיחות |
| `ENCAPSULATED_DATA` | סטטוס מרוץ, struct `"<BQqqIq"` | ראו פירוט מטה |

מבנה סטטוס המרוץ (`ENCAPSULATED_DATA`, struct `"<BQqqIq"`):

```
data_type, sim_boot_time_ms, race_start_boot_time_ms,
race_finish_time_ns, active_gate_index, last_gate_race_time
```

### 2.3 מה הסימולטור מנטרל בכוונה

- הודעות `ATTITUDE`, `LOCAL_POSITION_NED`, `ODOMETRY` — **מושבתות**.
- מיקומי השערים — **מאופסים (nulled)**.
- המשמעות: אין שום "אורקל מצב". שחזור attitude, מהירות ומיקום יחסי — כולו עלינו.
- החריג היחיד: `active_gate_index` הוא האורקל היחיד למעבר שער — וגם אות ה-reward של לולאת הלמידה.

### 2.4 וידאו

פריימים של מצלמת FPV מגיעים כ-JPEG על UDP בפורט **5600**, בפקטות מחולקות (chunked). כותרת כל פקטה היא struct `"<IHHIIQ"`:

```
frame_id, chunk_id, total_chunks, jpeg_size, payload_size, sim_time_ns
```

### 2.5 איפוס אוטומטי

פקודת MAVLink מספר **31000** מאפסת את הסימולטור — זה מה שמאפשר קמפיינים אוטומטיים של טיסה-אחר-טיסה ללא מגע יד אדם (מסמך [04](04-lulaat-lemida.md)).

### 2.6 מגבלת סביבת פיתוח

הסימולטור רץ **רק על מכונת ה-Windows של המשתמש**. כל הפיתוח וה-CI במאגר הזה רצים מול סימולטור mock ומול הקלטות (record/replay) — ראו מסמך [06](06-bdikot-veshichzur.md).

## 3. אילוצי התכן המרכזיים

1. **ראייה + IMU בלבד** — ללא GPS וללא טלמטריית מצב. מכאן עקרון "מצב יחסי-לשער" (gate-relative state) ולא מצב גלובלי: מיקום גלובלי משוחזר-אינרציאלית סוחף ללא גבול.
2. **לולאת בקרה ב-250Hz** — תקציב של 4ms לכל tick, בתהליך Python יחיד. הלולאה החמה קדושה: ללא הקצאות זיכרון, ללא חסימות, תזמון absolute-deadline.
3. **הכל מוקלט וניתן לשחזור** — לוגי טיסה JSONL + הקלטת UDP גולמית + שרת replay.
4. **פרמטרים הם דאטה** — כל ערך כוונון חי ב-`ParamSet` ממוגרס (JSON), עם hash וצילום-מצב פר טיסה. זה המצע לכוונון אוטומטי.

## 4. יעדים לפי סבבי המוקדמות

### סבב 1 (סביבה פשוטה, ניגודיות גבוהה)

- השלמת הקפות מלאות באמינות גבוהה עם גלאי HSV קלאסי + solvePnP.
- בקרת velocity setpoints מיוצבת, מעברי search → approach → commit → recover אמינים.
- קמפיין כוונון אוטומטי שמשפר זמן הקפה בלי מגע יד אדם (Phase 5).

### סבב 2 (סביבות 3D-scanned)

- החלפת הגלאי מאחורי ממשק `GateDetector` (ABC) בגלאי שמתמודד עם רקע מציאותי.
- מעבר ל-attitude-rate control‏ (Phase 6) לטובת מהירות — מכוונן על ידי הקמפיינים.

## 5. תוצרים (Deliverables)

| תוצר | מיקום | מסמך |
|---|---|---|
| חבילת `aigp` — שבעת הסוכנים + core | `src/aigp/` | [01](01-architektura.md) |
| סימולטור mock ולוגיקת replay | `simtools/` | [06](06-bdikot-veshichzur.md) |
| סקריפטים תפעוליים למכונת Windows | `scripts/` (למשל `scripts/fly_once.py`, `scripts/frame_probe.py`) | [05](05-avney-derech.md) |
| בדיקות יחידה ואינטגרציה | `tests/` | [06](06-bdikot-veshichzur.md) |
| מסד תוצאות SQLite + לוגי JSONL | פלטי ריצה | [04](04-lulaat-lemida.md) |
| סט מסמכי תכנון זה | `docs/` | — |

## 6. מפת המסמכים

| מסמך | נושא |
|---|---|
| `docs/00-skira-klalit.md` | המסמך הזה — תחרות, אילוצים, יעדים, מילון מונחים |
| `docs/01-architektura.md` | ארכיטקטורה רב-סוכנית, ה-bus, מודל התהליכונים, עץ המאגר |
| `docs/02-bakara-veshichzur-matzav.md` | סולם מצבי בקרה, פילטר Mahony, ‏VIO-lite, ‏RateLoop |
| `docs/03-reiya.md` | צינור המצלמה, גלאי סבב 1, ‏PnP, חלון עיוור, סבב 2 |
| `docs/04-lulaat-lemida.md` | ‏ParamSet, לוגים, ניקוד, אופטימיזציה, קמפיינים |
| `docs/05-avney-derech.md` | פאזות, קריטריוני קבלה, צ'קליסטים ל-Windows, סיכונים |
| `docs/06-bdikot-veshichzur.md` | שלושת שלבי הבדיקות, mock sim, הקלטה/שחזור, CI |

## 7. מילון מונחים

| מונח | פירוש |
|---|---|
| MAVLink | פרוטוקול תקשורת סטנדרטי לכלי טיס בלתי מאוישים; ערוץ הבקרה והטלמטריה שלנו מעל UDP |
| IMU | Inertial Measurement Unit — יחידת מדידה אינרציאלית (accelerometer + gyroscope), כאן דרך `HIGHRES_IMU` |
| FPV | First Person View — מצלמת "גוף ראשון" המורכבת על הרחפן; מקור הווידאו היחיד שלנו |
| NED | North-East-Down — מערכת צירים מקומית מקובלת בתעופה; רלוונטית ל-`set_position_target_local_ned` |
| BODY frame | מערכת צירים צמודת-גוף של הרחפן; שאלת ה-NED-vs-BODY פתוחה ונבדקת ב-`scripts/frame_probe.py` |
| PnP | Perspective-n-Point — שחזור pose של המצלמה יחסית לאובייקט ממופה (פינות השער) מתוך תמונה בודדת; אצלנו `cv2.solvePnP` |
| VIO | Visual-Inertial Odometry — שילוב ראייה ואינרציה לשחזור תנועה; אצלנו גרסה מינימלית, "VIO-lite" |
| FSM | Finite State Machine — מכונת מצבים סופית; ליבת ה-Supervisor ב-`race_manager.py` |
| PID | בקר Proportional-Integral-Derivative; ליבת ה-AttitudeRateBackend בשלב 6 |
| CEM | Cross-Entropy Method — אלגוריתם אופטימיזציה סטוכסטי, שלב הביניים בסולם האופטימייזרים |
| CMA-ES | Covariance Matrix Adaptation Evolution Strategy — אופטימיזציית קופסה-שחורה; היעד בסולם האופטימייזרים |
| RL | Reinforcement Learning — למידת חיזוק; לא בשימוש כעת, אך קיים hook עתידי (מסמך 04) |
| HSV | Hue-Saturation-Value — מרחב צבע לגלאי הקלאסי של סבב 1 |
| JSONL | JSON Lines — שורת JSON לרשומה; פורמט לוגי הטיסה |
| GIL | Global Interpreter Lock של CPython; שיקול מרכזי בתכנון ה-threading (מסמך 01) |
| ABC | Abstract Base Class בפייתון; מנגנון ההחלפה של `GateDetector` ו-`ControlBackend` |
| Gate-relative pose | ה-pose של הרחפן ביחס לשער הפעיל — יחידת המצב הבסיסית שלנו, במקום מיקום גלובלי |
| Blind window / commit | חלון הזמן שבו השער יוצא משדה הראייה סמוך למעבר; נטוס בו "על עיוור" בווקטור נעול |
| ParamSet | אוסף כל הפרמטרים הניתנים לכוונון, JSON ממוגרס עם sha256 hash |
| Campaign | סדרת טיסות אוטומטית: ask → patch → reset → fly → score → tell |

## 8. עיקרון מנחה לקריאת המסמכים

כל החלטה תכנונית במסמכים הבאים נובעת מאחד מארבעת האילוצים בסעיף 3. כשמופיעה שאלה פתוחה (למשל סמנטיקת ה-frame של velocity setpoints), היא מסומנת ככזו יחד עם תוכנית הניסוי שתסגור אותה — איננו מניחים תשובות שהסימולטור האמיתי טרם אישר.
