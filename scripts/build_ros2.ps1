# Build all ROS 2 packages with colcon.
#
# Environment variables:
#   ROS2_ROOT  (optional) Path to ROS 2 install, default C:\dev\ros2_jazzy

$ErrorActionPreference = "Stop"

$ros2Root = if ($env:ROS2_ROOT) { $env:ROS2_ROOT } else { "C:\dev\ros2_jazzy" }
$ros2Setup = "$ros2Root\setup.bat"
if (-not (Test-Path $ros2Setup)) {
    Write-Error "ERROR: ROS 2 not found at $ros2Setup. Set ROS2_ROOT to override."
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

Set-Location ros2_ws
colcon build --symlink-install
exit $LASTEXITCODE
