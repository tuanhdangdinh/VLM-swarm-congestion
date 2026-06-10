# Run M6 Isaac Sim simulation.
# Usage: .\scripts\run_simulation.ps1 --scenario head_on_deadlock --headless --seed 42 --repetitions 3
#
# Environment variables:
#   ISAAC_SIM_ROOT  (required) Path to Isaac Sim install dir, e.g. C:\isaac-sim
#   ROS2_ROOT       (optional) Path to ROS 2 Jazzy install, default C:\dev\ros2_jazzy

$ErrorActionPreference = "Stop"

if (-not $env:ISAAC_SIM_ROOT) {
    Write-Error "ERROR: ISAAC_SIM_ROOT is not set. Set it to your Isaac Sim install directory."
    exit 1
}
if (-not (Test-Path "$env:ISAAC_SIM_ROOT\python.bat")) {
    Write-Error "ERROR: $env:ISAAC_SIM_ROOT\python.bat not found."
    exit 1
}

$ros2Root = if ($env:ROS2_ROOT) { $env:ROS2_ROOT } else { "C:\dev\ros2_jazzy" }
$ros2Setup = "$ros2Root\setup.bat"
if (-not (Test-Path $ros2Setup)) {
    Write-Error "ERROR: ROS 2 Jazzy not found at $ros2Setup. Set ROS2_ROOT to override."
    exit 1
}

function Invoke-BatchEnv {
    param([string]$BatFile)
    $raw = cmd /c "call `"$BatFile`" && set 2>nul"
    foreach ($line in $raw) {
        if ($line -match "^([^=]+)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
        }
    }
}

Invoke-BatchEnv $ros2Setup

$wsSetup = "ros2_ws\install\setup.bat"
if (Test-Path $wsSetup) {
    Invoke-BatchEnv (Resolve-Path $wsSetup).Path
}

& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.run_simulation @args
exit $LASTEXITCODE
