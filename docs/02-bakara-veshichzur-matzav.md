# 02 — בקרה ושחזור מצב

מסמך זה מפרט את שני החצאים הצמודים של הטיסה עצמה: איך משחזרים את מצב הרחפן ללא GPS וללא טלמטריית attitude, ואיך מתרגמים כוונה תכנונית לפקודות בקצב 250Hz.

## 1. סולם מצבי הבקרה (control-authority ladder)

הסימולטור מציע שלושה מצבי בקרה. אנחנו מטפסים עליהם בהדרגה, דרך ממשק `ControlBackend` אחיד (`src/aigp/control/interface.py`), כך שהחלפת שלב היא החלפת מימוש ולא שכתוב:

| שלב בסולם | הודעת MAVLink | מי מייצב את מה | מתי |
|---|---|---|---|
| 1. Velocity | `set_position_target_local_ned` — velocity setpoints | הבקר הפנימי של הסימולטור מייצב attitude | מהיום הראשון (Phase 2) |
| 2. Attitude-rate | `set_attitude_target` — body rates [rad/s] + collective thrust 0..1 | אנחנו מייצבים attitude; הסים רק מסובב מנועים | ‏Phase 6 |
| 3. Motor RPM | `set_actuator_control_target` — RPM ל-`[FL, FR, BL, BR]` | אנחנו מייצבים הכל, כולל את קצב הסל"ד עצמו | עתידי; `motor_backend.py` הוא stub |

### 1.1 הרציונל להתחלה ב-velocity setpoints

- **טיסה יציבה מהיום הראשון**: הסימולטור מכיל flight controller פנימי; velocity setpoints נותנים לנו רחפן שלא מתהפך עוד לפני שיש לנו estimator שלם. זה מקצר דרמטית את הדרך ל-Phase 3–4 (מעברי שערים) — הערך התחרותי האמיתי.
- **בידוד כשלים**: כשמשהו נכשל בשלבים המוקדמים, אנחנו יודעים שזה לא ייצוב ה-attitude שלנו.
- **תקרת ביצועים ידועה**: בקר המהירות הפנימי שמרן; בשביל מהירות מרוץ אמיתית נצטרך את שלב 2. לכן AttitudeRateBackend הוא Phase 6 מפורש עם קריטריון קבלה ("משלים מסלול כמו velocity backend, במהירות גבוהה יותר"), לא שאיפה עמומה.

### 1.2 חוזה ה-`ControlBackend`

כל backend מקבל את אותו קלט — פקודת תכנון (וקטור מהירות רצוי + yaw רצוי, במונחי המצב המשוערך) ו-`StateEstimate` — ומחזיר הודעת MAVLink מוכנה לשידור. ה-planner לא יודע ולא צריך לדעת איזה backend פעיל.

- `velocity_backend.py`: עיצוב setpoint (שיפועי תאוצה מותרים, slew limits על שינוי הפקודה) — כל המגבלות ב-`ParamSet`.
- `attitude_rate_backend.py`: הקסקדה של סעיף 5.
- `motor_backend.py`: stub, שומר את המשבצת בסולם.

## 2. השאלה הפתוחה: NED או BODY?

**הבעיה**: ‏`set_position_target_local_ned` מקבל velocity setpoints, אך לא ידוע אם הסימולטור מכבד `MAV_FRAME_BODY_NED` (מהירות במערכת הגוף — "קדימה שלי") או רק `LOCAL_NED` (מערכת עולם). אם רק LOCAL_NED — יש לנו בעיה אמיתית: אין לנו yaw גלובלי, כי אין טלמטריית attitude ואין GPS. פקודת "צפונה" חסרת משמעות כשלא יודעים איפה צפון.

**תוכנית הבדיקה — `scripts/frame_probe.py`** (רץ על מכונת ה-Windows, חלק מ-Phase 1):

1. המראה ו-hover בעזרת setpoint אנכי בלבד (זהה בשתי המערכות).
2. שליחת פקודת מהירות אופקית קבועה, פעם עם `MAV_FRAME_BODY_NED` ופעם עם `MAV_FRAME_LOCAL_NED`, תוך סיבוב yaw איטי.
3. ניתוח ההקלטה: אם התאוצה הנמדדת ב-`HIGHRES_IMU` (במערכת הגוף) נשארת קבועה תוך כדי הסיבוב — הסים מכבד BODY frame. אם היא מסתובבת ביחס לגוף — הפקודה מתבצעת במערכת העולם.
4. ההקלטה נשמרת כ-fixture; המסקנה מתועדת כאן ובקוד.

**נתיבי פעולה לפי התוצאה**:

- ‏BODY נתמך → פשוט: ה-planner חושב ממילא במונחי gate-relative שקרובים לגוף.
- רק LOCAL_NED → ‏fallback: ה-estimator מתחזק yaw יחסי (אינטגרציית gyro מרגע ההמראה, מתוקנת מול נורמל השער כשיש ראייה) ומסובב את פקודת המהירות מגוף לעולם לפני השידור. סחיפת ה-yaw נסבלת כי היא מתאפסת מול כל שער.

## 3. שחזור מצב

### 3.1 הפילוסופיה: מצב יחסי-לשער, לא גלובלי

ללא GPS, אינטגרציה אינרציאלית של מיקום גלובלי סוחפת **ללא גבול** — שגיאת accelerometer קבועה הופכת לשגיאת מיקום שגדלה ריבועית בזמן. לכן:

- יחידת המצב הבסיסית היא **pose יחסית לשער הפעיל**, שמגיעה מהראייה (PnP) ומתעדכנת בכל detection.
- ‏dead-reckoning אינרציאלי משמש רק **לגשר על נתקי ראייה קצרים** (שניות בודדות לכל היותר — blur, שער מחוץ ל-FOV) — בטווח הזה הסחיפה קטנה וחסומה.
- מעבר שער מאפס את הבעיה: שער חדש, pose יחסית חדשה, שגיאה מצטברת נמחקת.

אין לנו — ולא צריך שיהיה לנו — מפה גלובלית של המסלול.

### 3.2 פילטר ה-attitude — `attitude_filter.py`

פילטר Mahony/complementary קלאסי:

- **חיזוי**: אינטגרציית gyro (quaternion integration) בכל דגימת `HIGHRES_IMU`.
- **תיקון**: וקטור הכבידה הנמדד ב-accelerometer מושך את הערכת ה-roll/pitch חזרה לאנך; משקל התיקון קטן כשהתאוצה הכוללת רחוקה מ-1g (כלומר כשהרחפן מתמרן והמדידה "מזוהמת" בתאוצה קווית).
- **מה לא מתוקן**: ‏yaw — ל-accelerometer אין מידע על yaw ואין לנו מגנטומטר. ‏yaw נצבר מ-gyro בלבד ומטופל כיחסי (ראו 2 ו-3.3).
- gains של הפילטר — ב-`ParamSet`.

הבחירה ב-Mahony ולא ב-EKF: סדר גודל פחות קוד, התנהגות צפויה, ומספיק טוב כשהתיקון האמיתי מגיע מהראייה. משבצת השדרוג מבודדת — הפלט הוא quaternion + body rates, ומחליף עתידי מספק את אותו הפלט.

### 3.3 VIO-lite — `state_estimator.py`

לא VIO אמיתי (אין feature tracking, אין optimization window). הרעיון:

1. **מהירות**: תאוצת ה-accelerometer מסובבת לעולם-מקומי לפי ה-attitude המשוערך, מפוצת כבידה, ומאונטגרלת למהירות.
2. **ריסון ותיקון**: דלתות ה-pose היחסי מהראייה (שינוי המרחק/הכיוון לשער בין detections) גוזרות מהירות "נצפית"; המהירות האינרציאלית נמשכת אליה (complementary blend), ומרוסנת (damping) כשאין ראייה — עדיף אומדן שמתכווץ לאפס מאומדן שבורח.
3. **‏gate_rel pose**: מגיעה מ-PnP כשיש detection; בין detections היא מתקדמת ב-dead-reckoning מהמהירות המשוערכת. שדה `age` חושף כמה ישן העדכון החזותי האחרון.

פלט — dataclass ‏`StateEstimate`:

```python
@dataclass(frozen=True)
class StateEstimate:
    q: Quaternion          # attitude
    body_rates: Vec3       # [rad/s]
    velocity: Vec3         # משוערכת
    gate_rel: RelPose      # pose יחסית לשער הפעיל
    gate_rel_age_s: float  # גיל העדכון החזותי האחרון
    health: EstimatorHealth
```

### 3.4 תקציב סחיפה (drift budget)

| מקטע | משך אופייני | מקור המצב | סחיפה נסבלת |
|---|---|---|---|
| approach עם ראייה | רציף | ‏PnP בכל פריים | ~אפס — מתאפס כל detection |
| נתק ראייה רגעי (blur, תאורה) | < 0.5s | ‏dead-reckoning | סנטימטרים — זניח |
| חלון עיוור (commit) | ‏`commit_duration_s` (~0.5–1.5s) | וקטור נעול + ‏dead-reckoning | עשרות ס"מ — חייב להיות קטן מחצי מרווח הבטיחות בשער |
| search אחרי איבוד | עד שהגלאי יורה | ‏hover, מהירות ~0 | לא רלוונטי — עומדים במקום |

המסקנות התכנוניות: (א) `commit_duration_s` הוא פרמטר קריטי בטיחותית ולכן בין הראשונים בכוונון האוטומטי; (ב) ה-watchdog על staleness של פריימים (>500ms) קיים בדיוק כי מעבר לזה ה-dead-reckoning כבר לא אמין; (ג) לעולם לא טסים מהר בלי ראייה מחוץ לחלון ה-commit המתוכנן.

## 4. תזמון — `RateLoop` ב-`core/scheduler.py`

לולאת 250Hz נאיבית (`sleep(1/250)` בסוף כל איטרציה) צוברת פיגור: זמן העיבוד מתווסף לשינה, והקצב האפקטיבי יורד וסוחף. במקום זה:

```python
deadline = t0 + k * period          # deadline אבסולוטי לכל tick k
sleep(max(0, deadline - now()))     # ישנים עד ה-deadline, לא "פרק זמן"
if now() > deadline + tolerance:
    overrun_count += 1              # מטריקה, לא הדפסה
```

- ‏deadlines נגזרים מ-`t0` קבוע — jitter של איטרציה אחת לא מזהם את הבאות.
- מטריקות: יחס overruns, התפלגות זמן-tick — מדווחות ללוג ונבדקות בקריטריון הקבלה של Phase 2 (פחות מ-1% overruns).
- מדיניות חריגה: אם ה-tick חרג — לא מדלגים על שידור, אלא ממשיכים מיד ל-deadline הבא; ה-watchdog של ה-Supervisor עוקב אחרי היחס.
- ‏fallback מתוכנן: ה-VelocityBackend סובל decimation ל-125Hz אם Python לא עומד בקצב על החומרה הנתונה; ל-AttitudeRateBackend (Phase 6) זה לא מקובל, ושם נכריע לפי המדידות בפועל.

### חוקי הלולאה החמה

1. אפס הקצאות זיכרון בנתיב החם (מבנים נוצרים פעם אחת, סקלרים מתעדכנים).
2. אפס קריאות חוסמות — רק `get()` על `LatestValue`.
3. אפס I/O — לוגינג דרך tap שרק "מציע" (offer) ומפיל בעומס.
4. תקציב: 4ms לכל tick, נמדד ומדווח תמיד.

## 5. קסקדת ה-PID לשלב 6 — `attitude_rate_backend.py`

כשעוברים ל-`set_attitude_target` אנחנו לוקחים על עצמנו את ייצוב ה-attitude. המבנה:

```
שגיאת מהירות (רצויה − משוערכת), במערכת עולם-מקומי
        │  P(+I מוגבל) על שגיאת מהירות
        ▼
וקטור תאוצה רצוי  ──►  פירוק ל-tilt רצוי (roll/pitch) + collective thrust
        │                (נורמליזציית thrust ל-0..1; הגבלת זווית tilt מקסימלית)
        ▼
שגיאת attitude (רצוי − משוערך מ-attitude_filter)
        │  P על שגיאת זווית → body rates רצויים
        ▼
PID על body rates (מול gyro) ──►  set_attitude_target(body_rates, thrust)
```

- המימוש ב-`pid.py`: בקר PID עם **anti-windup** (הקפאת אינטגרטור ברוויה) ו-clamp על הפלט.
- כל ה-gains, מגבלות ה-tilt וה-thrust — ב-`ParamSet`, כלומר ניתנים לכוונון על ידי קמפיין (זה בדיוק איך Phase 6 יכוונן: הקמפיין של Phase 5 רץ על gains של הקסקדה).
- הלולאה הפנימית (body rates) היא הצרכן האמיתי של 250Hz; הלולאות החיצוניות יכולות לרוץ decimated.

## 6. סיכום החלטות ושאלות פתוחות

| נושא | החלטה | סטטוס |
|---|---|---|
| מצב בקרה התחלתי | velocity setpoints דרך `VelocityBackend` | סגור |
| ‏frame של velocity | לא ידוע — ‏`frame_probe.py` ב-Phase 1 | **פתוח** |
| פילטר attitude | Mahony/complementary, לא EKF | סגור (משבצת שדרוג מבודדת) |
| מקור yaw | יחסי בלבד: gyro + התיישרות מול נורמל השער | סגור |
| מצב גלובלי | אין. gate-relative בלבד + ‏dead-reckoning קצר | סגור |
| תזמון | ‏`RateLoop` ‏absolute-deadline + מטריקות | סגור |
| ‏attitude-rate cascade | ‏Phase 6, ‏gains מקמפיין | סגור, מותנה במדידות תזמון |
