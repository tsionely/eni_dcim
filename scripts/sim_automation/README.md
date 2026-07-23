# Local simulator automation

Legacy Windows GUI helpers copied from the local simulator workstation so the
race lead can review and harden them in git. They currently use title-based
window discovery; foreground-by-process ownership, the login gate, and the
v1.0.3390 banner assertion are intentionally left for the lead's review.

## Entrypoints

- `launch_sim.ps1` - launches
  `C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe`.
- `event_select.py <event> <label> [dialog|scene]` - navigates to the active
  event list, template-matches the requested row, captures verification
  screenshots, and selects it. Event keys are `r1`, `r2submission`, and
  `r2training`.
- `race_click_capture.py <label>` - clicks the RACE control, checks for the
  cyan R2 scene, and captures periodic screenshots.
- `shot_only.py [output.png]` - records the foreground-window title and saves
  one desktop screenshot.
- `sim_window_utils.py` - copied support module containing `sim_window`,
  `_sim_focus`, `_sim_click`, `_sim_key`, and the original screenshot/launcher
  utilities used by the helpers.

Use the repository venv explicitly:

```powershell
C:\Users\tsion\Projects\eni_dcim\.venv\Scripts\python.exe scripts\sim_automation\event_select.py r2training example dialog
```

The copied GUI helpers require `pyautogui`, `pygetwindow`, OpenCV, and NumPy.
Install any missing GUI dependencies into that repository venv before running
the entrypoints; do not fall back to the broken system `python` or `py`
launchers.

## Templates

All templates live under `templates/`:

- `r1_label_template.png` - the **AI-GP VIRTUAL QUALIFIER R1** event row.
- `r2submission_label_template.png` - the **AI-GP VIRTUAL QUALIFIER R2 -
  SUBMISSION** event row.
- `r2training_label_template.png` - the **AI-GP VIRTUAL QUALIFIER R2 -
  TRAINING** event row.

The event-selection acceptance threshold is **0.80**. The helper searches
nearby scales (`0.90` through `1.10`) and must match every event-row template
at or above that score before it clicks a row.
