# 05 — אבני דרך

מפת הדרכים בנויה משבע פאזות (0–6), כל אחת עם פירוק משימות, קריטריוני קבלה מדידים, וצ'קליסט קצר למכונת ה-Windows של המשתמש (המקום היחיד שבו הסימולטור האמיתי רץ). דפוס העבודה קבוע: מפתחים ובודקים כאן מול mock והקלטות ← המשתמש מריץ צ'קליסט קצר על Windows ← ההקלטות חוזרות לכאן כ-fixtures.

## סיכום-על

| פאזה | שם | קריטריון קבלה מרכזי |
|---|---|---|
| 0 | שלד + מסמכים | בדיקות יחידה ירוקות; לולאה סגורה מול mock: ‏connect→arm→hover→reset נקי |
| 1 | קישוריות לסים האמיתי | 60s טלמטריה+פריימים בלוג; ‏timesync offset std < 5ms; הקלטה; ‏frame_probe מוכרע |
| 2 | ‏hover והמראה יציבים | ‏30s hover, ‏0 התנגשויות, ‏10/10 ניסיונות, ‏overruns < 1% |
| 3 | שער אחד | ‏≥8/10 מעברים (`active_gate_index` עולה); ‏detection > 80% מהפריימים בטווח 15m |
| 4 | מסלול מלא | ‏≥7/10 הקפות מלאות (`race_finish_time_ns` מתקבל); כל הטיסות בלוג + ‏SQLite |
| 5 | קמפייני כוונון | קמפיין ≥20 טיסות ללא השגחה; שיפור ≥15% בהקפה הטובה מול baseline של Phase 4; שחזור מה-DB |
| 6 | מהירות + סבב 2 | ‏att-rate משתווה ל-velocity בהשלמה במהירות גבוהה יותר; גלאי סבב 2 עובד על הקלטות |

---

## Phase 0 — שלד + מסמכים (עכשיו)

**משימות**

- עץ החבילה `src/aigp/` המלא (מסמך 01) עם ממשקים: ‏bus, ‏messages, ‏clock, ‏params, ‏scheduler.
- ‏`simtools/mock_sim.py` (מסמך 06) + לולאה סגורה מולו.
- ‏FSM של ה-Supervisor + בדיקת טבלת מעברים.
- בדיקות יחידה: ‏bus, ‏ParamSet, ‏PID, ‏clock, ‏FSM, הרכבת chunks, גלאי על תמונות סינתטיות.
- סט המסמכים הזה.

**קבלה**: כל בדיקות היחידה ירוקות; מול ה-mock: ‏connect→arm→hover→reset ללא שגיאות וללא watchdog.

**‏Windows**: אין — הפאזה כולה כאן.

---

## Phase 1 — קישוריות לסים האמיתי

**משימות**

- התאמת `mavlink_io.py` / ‏`vision_rx.py` להתנהגות האמיתית של `FlightSim.exe` (הפתעות wire-format צפויות).
- ‏`timesync.py` מול הסים; מדידת יציבות ה-offset.
- ‏`simtools/record.py` רץ על Windows ומקליט הכל; ‏`io/udp_tap.py` פעיל.
- ‏`scripts/frame_probe.py` — הכרעת שאלת NED-vs-BODY (מסמך 02, סעיף 2).

**קבלה**: 60 שניות של טלמטריה + פריימים נקלטות ונרשמות; סטיית התקן של offset ה-TIMESYNC < ‏5ms; קובץ הקלטה תקין שמתנגן ב-`replay_server.py`; מסקנת frame_probe מתועדת.

**צ'קליסט Windows**

1. הפעלת `FlightSim.exe` והתחברות לחשבון הסימולטור; ‏`python scripts/phase1_check.py --duration 60` — סקריפט פסיבי (לא מחמש ולא שולח פקודות): מדפיס דוח קצבים (IMU/פריימים/race status), ‏timesync offset ופסיקת PASS/FAIL על כל קריטריוני הקבלה, ומקליט אוטומטית ל-`recordings/phase1-<ts>.aigprec`.
2. אם עבר — ‏`python scripts/fly_once.py --max-duration 20` לטיסה מבוקרת ראשונה (arm + המראה + חיפוש).
3. ‏`python scripts/frame_probe.py` ושמירת הפלט (`logs/frame_probe/probe.json`); עדכון `control.velocity.frame` ב-`config/params_default.json` לפי המסקנה.
4. העברת תיקיית ההקלטות + הלוגים חזרה למאגר (commit או העלאה לסשן).

---

## Phase 2 — ‏hover והמראה יציבים

**משימות**

- ‏`VelocityBackend` מלא (עיצוב setpoint, ‏slew limits).
- ‏`attitude_filter.py` (Mahony) רץ ומולוגג; השוואה מול ההקלטות.
- ‏watchdogs: ‏IMU staleness ‏>50ms, ‏frame staleness ‏>500ms, יחס overruns; מדיניות abort ב-`safety.py`.
- מסלול FSM: ‏IDLE→…→TAKEOFF→hover→RESETTING.

**קבלה**: ‏hover של 30 שניות, אפס התנגשויות, ‏10/10 ניסיונות רצופים; ‏loop overruns < 1% לאורך הריצה.

**צ'קליסט Windows**

1. ‏`python scripts/fly_once.py --mode hover --repeat 10`.
2. מעקב: כל ניסיון מסתיים ב-RESETTING נקי, לא ב-ABORT.
3. שליחת הלוגים + פלט מטריקות ה-RateLoop חזרה.

---

## Phase 3 — שער אחד

**משימות**

- ‏`gate_detector_hsv.py` מכויל על הקלטות Phase 1–2; כיול FOV אמפירי (מסמך 03, סעיף 4).
- ‏PnP + בדיקות שפיות; ‏`Detection` מוזרם ל-estimator (תיקוני VIO-lite פעילים).
- ‏`race_planner.py`: ‏search → approach → commit; אישור מעבר דרך `active_gate_index`.

**קבלה**: ‏≥8/10 מעברי שער-בודד (`active_gate_index` עולה); ‏detection תקפה ביותר מ-80% מהפריימים בטווח 15m.

**צ'קליסט Windows**

1. סצנת שער בודד; ‏`python scripts/fly_once.py --mode single_gate --repeat 10`.
2. רישום: מעברים, ‏detection rate מהסיכום בסוף טיסה, התנגשויות.
3. אם ה-detection נמוך — הרצת מקטע ההקלטה חזרה אלינו לפני כוונון ידני.

---

## Phase 4 — מסלול מלא

**משימות**

- רצף שערים (השער הפעיל לפי `active_gate_index`), חלון עיוור מלא, ‏recover (‏lost-gate → בלימה → ‏search).
- מדיניות התנגשויות: סביבה threat_level 2 ← ‏abort; נגיעות שער נרשמות ונסבלות.
- ‏`flight_log.py` + ‏`results_db.py` + ‏`metrics.py` פעילים על כל טיסה.

**קבלה**: ‏≥7/10 הקפות מלאות (`race_finish_time_ns` מתקבל); כל הטיסות מנוקדות ורשומות ב-SQLite.

**צ'קליסט Windows**

1. מסלול מלא; ‏`python scripts/fly_once.py --mode race --repeat 10`.
2. וידוא שכל טיסה מופיעה ב-`results.db` עם score.
3. שליחת `results.db`, הלוגים והקלטה של ההקפה הטובה ביותר (fixture עתידי).

---

## Phase 5 — קמפייני כוונון אוטומטיים

**משימות**

- ‏`optimizers.py` (RandomSearch, ‏CEM) + ‏`campaign.py` על מנגנון ה-reset (cmd 31000).
- חוסן קמפיין: ‏timeout פר טיסה, ‏retry על reset, המשך אחרי abort.
- קמפיין מלא מול ה-mock ב-CI; ואז קמפיין אמיתי על מפתחות הכוונון הראשונים (מסמך 04, סעיף 6).

**קבלה**: קמפיין ≥20 טיסות ללא התערבות; ההקפה הטובה משתפרת ב-≥15% מול baseline של Phase 4; התוצאה ניתנת לשחזור מה-DB (שליפת הפרמטרים הטובים והרצה חוזרת).

**צ'קליסט Windows**

1. ‏`python scripts/fly_once.py --mode campaign --flights 20` (או `scripts/run_campaign.py`) והשארת המכונה עובדת.
2. בדיקה תקופתית שהקמפיין מתקדם (מונה טיסות עולה, אין תקיעה על reset).
3. שליחת `results.db` + לוגים; אימות שחזור: הרצת הפרמטרים הטובים פעם נוספת.

---

## Phase 6 — מהירות + סבב 2

**משימות**

- ‏`attitude_rate_backend.py`: הקסקדה ממסמך 02 סעיף 5; ‏gains מכווננים בקמפיין (אותו מנגנון, מפתחות חדשים).
- מדידות תזמון: האם 250Hz מלא נשמר בלולאה הפנימית (כאן ה-decimation כבר לא קביל).
- גלאי סבב 2 מאחורי `GateDetector` ABC, מפותח ונמדד על הקלטות סבב 2 (מסמך 03, סעיף 6).

**קבלה**: ‏AttitudeRateBackend משיג את שיעור ההשלמה של ה-VelocityBackend במהירות גבוהה יותר; הגלאי החדש עובד על הקלטות סבב 2 מאחורי אותו ממשק.

**צ'קליסט Windows**

1. הקלטת סשנים בסביבות סבב 2 (גם טיסה איטית/ידנית-מבוקרת מספיקה) — הדאטה קודם לגלאי.
2. השוואת backends: ‏`--backend velocity` מול `--backend attrate` על אותו מסלול, אותו מספר חזרות.
3. קמפיין gains ל-attrate; שליחת הכל חזרה.

---

## רשימת סיכונים (Risk Register)

| # | סיכון | השפעה | מיתיגציה | סטטוס |
|---|---|---|---|---|
| R1 | סמנטיקת frame של velocity לא ידועה (BODY_NED מול LOCAL_NED, ואין לנו yaw גלובלי) | חוסם בקרה אופקית שימושית | ‏`scripts/frame_probe.py` ב-Phase 1; ‏fallback: ‏yaw יחסי מה-estimator + סיבוב הפקודה לעולם | פתוח — נסגר ב-Phase 1 |
| R2 | ‏intrinsics של המצלמה לא מפורסמים | שגיאת סקאלה במרחק מ-PnP ← ‏commit שגוי | כיול FOV אמפירי (מסמך 03 סעיף 4); ‏FOV כרשומת `ParamSet` | מתוכנן — Phase 3 |
| R3 | ‏jitter ב-250Hz תחת Python/GIL | ‏overruns ← בקרה לא יציבה, במיוחד ב-attrate | ‏RateLoop עם מטריקות; נתיב חם רזה ללא הקצאות; ‏fallback decimation ל-125Hz ‏(velocity בלבד); הכרעה על attrate לפי מדידות | מנוהל שוטף |
| R4 | אובדן פקטות UDP (פריימים חלקיים, טלמטריה חסרה) | חורי ראייה, ‏estimator מזדקן | ‏partial-frame GC ב-`vision_rx`; ‏watchdogs על staleness; ‏dead-reckoning קצוב לגישור | ממומש בתכנון |
| R5 | הנחת מידות השער שגויה | הטיית סקאלה שיטתית בכל מרחקי ה-PnP | המידות רשומת `ParamSet` ניתנת לכוונון; ‏sanity חוצה-חיישנים מול אינטגרציית מהירות | מנוטר |
| R6 | סחיפת התנהגות הסימולטור בין גרסאות | קוד שעבד נשבר בלי אזהרה | הקלטות אמיתיות כ-fixtures רגרסיה (record/replay); הרצת הצ'קליסט הקצר אחרי כל עדכון sim | מתמשך |

## תלויות בין פאזות

- ‏R1 (frame semantics) חוסם את Phase 2 — לכן הוא ב-Phase 1.
- כיול ה-FOV (Phase 3) תלוי בהקלטות מ-Phase 1–2.
- ‏Phase 5 תלוי במדיניות reset אמינה שמוכחת כבר ב-Phase 2 (כל ניסיון hover מסתיים ב-reset).
- דאטה של סבב 2 (הקלטות) הוא תנאי מקדים לגלאי של Phase 6 — מוקלט מוקדם ככל האפשר, גם לפני שנוגעים בקוד הגלאי.
