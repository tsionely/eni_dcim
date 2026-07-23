# Launch the official AI-GP FlightSim v1.0.3390.
# Usage (from repo root):
#   powershell -File scripts/sim_automation/launch_sim.ps1
$ErrorActionPreference = "Stop"
$exe = "C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe"
$version = "1.0.3390"
if (-not (Test-Path $exe)) { throw "FlightSim.exe not found: $exe" }

$wd = Split-Path $exe -Parent
Write-Host "Starting AI-GP Simulator v${version}: $exe"
Start-Process -FilePath $exe -WorkingDirectory $wd
Write-Host "Simulator launched. Use the guarded automation steps before clicking an event."
