# Elyatim-CONTROL + OUR-VISION launcher. Brings the AI-GP sim to front, starts a race via the
# proven event+RACE clicks, runs the INTEGRATED stack (Elyatim's race.py reactive control, fed by
# our vision gate-mapper + odometry) while screen-capturing into C:\drone_watch\elyatim_vision_shots,
# then restores the 'Claude' window.
#   python run_elyatim_vision.py [duration_s]
import os
import subprocess
import sys
import time
from pathlib import Path

import pyautogui
import pygetwindow as gw

if os.environ.get("ELYATIM_BENCHMARK"):
    pyautogui.FAILSAFE = False

_ROOT = Path(__file__).resolve().parent
ELY = str(_ROOT / "elyatim_vision")
SHOTS = _ROOT / "elyatim_vision_shots"
LOG = str(_ROOT / "elyatim_vision_run.log")


def win(title):
    m = [w for w in gw.getAllWindows() if w.title.strip() == title]
    return m[0] if m else None


def _game_pids():
    """PIDs of the real sim processes (FlightSim / DCGame).

    Title-based discovery also matches a File Explorer window open on a
    folder named "AI-GP Simulator v..." — the val-run1 event-fail capture
    shows exactly that trap. Process ownership cannot be spoofed by a
    folder name.
    """
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if parts and parts[0].lower() in ("flightsim.exe",
                                          "dcgame-win64-shipping.exe"):
            try:
                pids.append(int(parts[1]))
            except (IndexError, ValueError):
                pass
    return pids


def _hwnds_for_pids(pids):
    """Visible top-level windows owned by the given PIDs."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                found.append(hwnd)
        return True

    user32.EnumWindows(_cb, 0)
    return found


def sim_window(ensure_visible: bool = False):
    """Find the AI-GP sim window BY PROCESS OWNERSHIP; title is fallback.

    Fails fast with SIM_NOT_RUNNING when no FlightSim/DCGame process
    exists — clicking blind at a captured desktop was the val-run1
    failure mode.
    """
    import re

    pids = _game_pids()
    if not pids:
        print("SIM_NOT_RUNNING: no FlightSim/DCGame process found — "
              "launch the sim (and log in) first", flush=True)
        return None
    owned = []
    for h in _hwnds_for_pids(pids):
        try:
            owned.append(gw.Win32Window(h))
        except Exception:
            pass
    candidates = [w for w in owned if w.width > 200 and w.height > 200] or owned
    if not candidates:
        # Process exists but no sizable window surfaced (startup/minimized
        # edge) — fall back to the legacy title match.
        candidates = [
            w for w in gw.getAllWindows()
            if w.title.strip() == "AI-GP"
            or w.title.strip().startswith("AI-GP Simulator")
        ]
    if not candidates:
        return None

    def _ver_key(w):
        m = re.search(r"v(\d+\.\d+\.\d+)", w.title)
        return m.group(1) if m else "0"

    candidates.sort(key=_ver_key, reverse=True)
    top_ver = _ver_key(candidates[0])
    same_ver = [w for w in candidates if _ver_key(w) == top_ver]
    # Multiple windows with same title: pick largest visible (main game view).
    visible = [w for w in same_ver if not w.isMinimized and w.width > 200 and w.height > 200]
    pool = visible or same_ver
    pool.sort(key=lambda w: w.width * w.height, reverse=True)
    w = pool[0]

    if ensure_visible:
        for _ in range(4):
            if not w.isMinimized and w.width > 200 and w.height > 200:
                break
            try:
                w.restore()
                time.sleep(0.5)
            except Exception:
                pass
            # Refresh handle — restore can change geometry/title match.
            refreshed = [
                x for x in gw.getAllWindows()
                if x.title.strip() == w.title.strip()
            ]
            if refreshed:
                refreshed.sort(key=lambda x: x.width * x.height, reverse=True)
                w = refreshed[0]
        if w.width < 200 or w.height < 200:
            print(
                f"WARNING: sim window still tiny ({w.width}x{w.height}); "
                "close duplicate sim instances and restore manually",
                flush=True,
            )
    return w


def _sim_focus(ai, refresh: bool = True):
    """Bring sim to foreground before UI automation (clicks were landing on Explorer)."""
    if refresh:
        w = sim_window(ensure_visible=True)
        if w is not None:
            ai = w
    for _ in range(2):
        try:
            ai.restore()
            time.sleep(0.2)
            ai.activate()
            time.sleep(0.25)
            break
        except Exception:
            time.sleep(0.2)
    return ai


def _sim_click(ai, x: int, y: int):
    ai = _sim_focus(ai)
    pyautogui.click(x, y)
    return ai


def _sim_key(ai, key: str):
    ai = _sim_focus(ai)
    pyautogui.press(key)
    return ai


# Training-only events. r2-submission is blocked unless --allow-submission (real race).
EVENT_ROW_Y = {
    "r1": 225,
    "r2-submission": 303,
    "r2-training": 381,
}
TRAINING_EVENTS = frozenset({"r1", "r2-training"})
DEFAULT_EVENT = os.environ.get("ELYATIM_EVENT", "r2-training")


def event_click_xy(event_key: str) -> tuple[int, int]:
    key = event_key.lower().replace("_", "-")
    if key not in EVENT_ROW_Y:
        raise ValueError(f"unknown event {event_key!r}; choose {list(EVENT_ROW_Y)}")
    return 400, EVENT_ROW_Y[key]


def main():
    args = [a for a in sys.argv[1:] if a.startswith("-")]
    pos = [a for a in sys.argv[1:] if not a.startswith("-")]
    compliant = "--compliant" in args or "--vision-sequencer" in args
    vis_debug = "--vis-debug" in args
    drift_probe = "--drift-probe" in args or os.environ.get("ELYATIM_DRIFT_PROBE", "").strip() in ("1", "true", "yes")
    use_capture = "--capture" in args or os.environ.get("ELYATIM_CAPTURE", "").strip() in ("1", "true", "yes")
    use_watcher = (
        "--watcher" in args
        or os.environ.get("ELYATIM_WATCHER", "").strip() in ("1", "true", "yes")
        or (use_capture and "--no-watcher" not in args)
    )
    stack = os.environ.get("ELYATIM_STACK", "v3379")
    for i, a in enumerate(sys.argv[1:]):
        if a == "--stack" and i + 2 < len(sys.argv):
            stack = sys.argv[i + 2]
    event_key = DEFAULT_EVENT
    config_name = "race_config_v3379.json" if stack == "v3379" else "race_config_hybrid.json"
    for i, a in enumerate(sys.argv[1:]):
        if a == "--event" and i + 2 < len(sys.argv):
            event_key = sys.argv[i + 2]
        if a == "--config" and i + 2 < len(sys.argv):
            config_name = sys.argv[i + 2]
    allow_submission = "--allow-submission" in args
    event_norm = event_key.lower().replace("_", "-")
    if event_norm not in TRAINING_EVENTS and not allow_submission:
        print(
            f"ERROR: event={event_key!r} is the real race — blocked. "
            f"Use --event r1 or --event r2-training for training only.",
            flush=True,
        )
        return 1
    dur = 220.0
    race_extra: list[str] = []
    if "--" in sys.argv:
        race_extra = sys.argv[sys.argv.index("--") + 1:]
    extra_set = frozenset(race_extra)
    pos = [a for a in pos if a != "--" and a not in extra_set]
    for i, a in enumerate(pos):
        if a.replace(".", "", 1).isdigit():
            dur = float(a)
    ai, cl = sim_window(ensure_visible=True), win("Claude")
    if ai is None:
        print("ERROR: AI-GP simulator window not found (launch FlightSim.exe first)", flush=True)
        return 1
    print(f"sim window: {ai.title.strip()} ({ai.width}x{ai.height})", flush=True)
    dupes = len([
        w for w in gw.getAllWindows()
        if w.title.strip().startswith("AI-GP Simulator")
        and "3379" in w.title
    ])
    if dupes > 1:
        print(
            f"WARNING: {dupes} v3379 sim windows open — close extras "
            "(clicks/vision UDP can desync)",
            flush=True,
        )
    SHOTS.mkdir(parents=True, exist_ok=True)
    if not use_capture:
        for o in SHOTS.glob("shot_*.png"):
            o.unlink()

    # Robustly bring the sim to the FOREGROUND. A bare activate() intermittently fails
    # ("code 18 - There are no more files") and the RACE click then lands on the covering
    # terminal -> the race never STARTS and the run is silently lost (rec6 froze this way).
    # minimize->restore->activate forces focus; retry a few times. (No maximize: it would
    # shift the fixed click coords for event/RACE.)
    if ai is None:
        ai = sim_window(ensure_visible=True)
    if ai is None:
        print("ERROR: AI-GP simulator window lost before focus", flush=True)
        return 1
    for _try in range(3):
        try:
            ai.minimize(); time.sleep(0.35)
            ai.restore();  time.sleep(0.35)
            ai.activate(); time.sleep(0.35)
            break
        except Exception as e:
            print(f"ai focus retry {_try}: {e}", flush=True); time.sleep(0.4)
    time.sleep(1.3)

    # Return to FLY menu if a prior run left pause/result screen (clears stale race state).
    ai = _sim_key(ai, "esc"); time.sleep(1.0)
    ai = _sim_click(ai, 472, 800); time.sleep(1.5)
    ai = _sim_click(ai, 1360, 840); time.sleep(1.5)

    # [v3379] FLY menu: pick event row (default R2 TRAINING only).
    ex, ey = event_click_xy(event_key)
    ai = _sim_click(ai, ex, ey); time.sleep(2.2)
    print(f"event={event_key} clicked ({ex},{ey}); controller starts before RACE",
          time.strftime("%H:%M:%S"), flush=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["PYTHONUNBUFFERED"] = "1"
    race_module = "aigp.race3379" if stack == "v3379" else "aigp.race"
    if stack == "v3379":
        race_args = ["--max-seconds", str(int(dur))]
        race_args.extend(race_extra)
    else:
        race_args = [
            "--no-plan",
            "--config", config_name,
            "--max-seconds", str(int(dur)),
            "--vel-damp", "0.42",
            "--vel-lpf-hz", "8.0",
            "--rec-near", "22",
            "--rec-max-s", "45",
            "--rec-stuck-s", "28",
            "--cmd-slew", "8.0",
            "--rec-hsp", "5.5",
            "--hvel-guard", "0",
            "--vel-ff", "0",
            "--turn-slow-deg", "0",
        ]
        race_args.extend(race_extra)
    print(f"stack={stack} module={race_module} config={config_name} dur={dur}s", flush=True)
    if compliant and stack != "v3379":
        race_args.append("--vision-sequencer")
        print("COMPLIANT mode: --vision-sequencer ON", flush=True)
    if vis_debug and stack != "v3379":
        race_args.append("--vis-debug")
        print("vis-debug: detailed vision/mapper log ON", flush=True)
    elif vis_debug and stack == "v3379":
        print("vis-debug: race3379 logs at 0.5s (built-in)", flush=True)
    if drift_probe and stack != "v3379":
        race_args.append("--drift-probe")
        print("drift-probe: IMU dead-reckoning drift logger ON", flush=True)
    if use_capture:
        print("capture: sim-window recorder ON (2 Hz + log overlay)", flush=True)
    if use_watcher:
        print("watcher: real-time flight watcher ON (advisory + post report)", flush=True)

    capture_agent = None
    capture_dir = None
    watcher_agent = None
    advisory_path = _ROOT / "flight_advisory.json"
    if use_capture:
        from datetime import datetime

        sys.path.insert(0, str(_ROOT / "tools"))
        from flight_capture_agent import FlightCaptureAgent  # noqa: PLC0415

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_dir = SHOTS / f"capture_{stamp}"
        capture_agent = FlightCaptureAgent(
            out_dir=capture_dir,
            log_path=Path(LOG),
            hz=2.0,
            overlay=True,
            scale=0.5,
        )

    if use_watcher:
        from datetime import datetime

        sys.path.insert(0, str(_ROOT / "tools"))
        from flight_watcher_agent import FlightWatcherAgent  # noqa: PLC0415

        watcher_out = _ROOT / "watcher_out" / datetime.now().strftime("%Y%m%d_%H%M%S")
        watcher_agent = FlightWatcherAgent(
            log_path=Path(LOG),
            advisory_path=advisory_path,
            out_dir=watcher_out,
            capture_dir=capture_dir,
            inbox_dir=_ROOT / "watcher_inbox",
        )

    if use_watcher:
        env["ELYATIM_ADVISORY"] = str(advisory_path)

    proc = subprocess.Popen(
        [sys.executable, "-m", race_module] + race_args,
        cwd=ELY, env=env, stdout=open(LOG, "w"), stderr=subprocess.STDOUT)

    # Wait until the controller is Armed (connected + telemetry OK), THEN click RACE.
    armed_deadline = time.time() + 35.0
    got_armed = False
    while time.time() < armed_deadline:
        try:
            if "Armed." in Path(LOG).read_text(encoding="utf-8", errors="replace"):
                got_armed = True
                break
        except OSError:
            pass
        time.sleep(0.25)
    if not got_armed:
        print("WARNING: controller never Armed; skipping RACE click", flush=True)
    else:
        time.sleep(0.5)
        ai = _sim_click(ai, 1730, 875); time.sleep(0.4)   # RACE -- pilot-ready screen
    ai = _sim_click(ai, 1555, 842); time.sleep(0.3)   # legacy warm-flow RACE
    ai = _sim_click(ai, 960, 900);  time.sleep(0.3)   # legacy v20.1 ready
    print("RACE clicked", time.strftime("%H:%M:%S"), flush=True)

    if capture_agent is not None:
        capture_agent.start()
    if watcher_agent is not None:
        watcher_agent.start()

    i = 0
    t0 = time.perf_counter()
    while proc.poll() is None and (time.perf_counter() - t0) < dur + 5:
        if capture_agent is None:
            try:
                img = pyautogui.screenshot()
                img = img.resize((img.width // 2, img.height // 2))
                img.save(SHOTS / f"shot_{i:03d}.png")
                i += 1
            except OSError:
                pass
            time.sleep(1.0)
        else:
            time.sleep(0.25)
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    if capture_agent is not None:
        summary = capture_agent.stop()
        try:
            sys.path.insert(0, str(_ROOT / "tools"))
            from analyze_flight_capture import analyze, write_report  # noqa: PLC0415

            report = analyze(capture_dir)
            write_report(capture_dir, report)
            print(f"capture analysis: {capture_dir / 'ANALYSIS.md'}", flush=True)
            print(f"capture summary: gates={report.get('gates_passed', 0)} frames={report.get('frames', 0)}", flush=True)
        except Exception as e:
            print(f"capture analysis failed: {e}", flush=True)
        i = capture_agent.frame_count

    if watcher_agent is not None:
        watcher_agent.capture_dir = capture_dir
        wsum = watcher_agent.stop()
        print(f"watcher summary: gates={wsum.get('gates', 0)} alerts={wsum.get('alerts', 0)}", flush=True)
        print(f"watcher inbox: {_ROOT / 'watcher_inbox' / 'latest'}", flush=True)

    # Back to main menu (clean state).
    try:
        ai.activate()
    except Exception:
        pass
    time.sleep(0.8)
    # Return to the FLY menu for the next run. ESC opens the in-race pause menu (mid-race) whose
    # "BACK TO MAIN MENU" is at (472,800); after a clean FINISH the result screen is up instead,
    # whose "MAIN MENU" is bottom-centre (~1360,840). Click both -- whichever screen is showing,
    # one lands and the other is inert. (Coords proven/observed by hand 2026-06-14.)
    pyautogui.press("esc"); time.sleep(1.5)
    pyautogui.click(472, 800); time.sleep(2.0)    # pause-menu BACK TO MAIN MENU
    pyautogui.click(1360, 840); time.sleep(2.0)   # result-screen MAIN MENU (fallback)

    # Reveal the Claude window.
    try:
        ai.minimize()
    except Exception as e:
        print("ai.minimize:", e)
    time.sleep(0.6)
    try:
        cl.activate()
    except Exception:
        pass
    time.sleep(0.6)
    print(f"done: {i} shots; reset to main menu; sim minimized -> Claude visible", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
