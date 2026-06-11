# Always-on launcher for the super_crawler agent (dashboard + runtime loop).
# Restarts the process if it crashes; writes logs under deploy\logs\.
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File start_super_crawler.ps1

$ErrorActionPreference = "Continue"

$root    = Split-Path -Parent $PSScriptRoot            # ...\project-template
$crawler = Join-Path $root "_reference_super_crawler"
$python  = Join-Path $root ".venv\Scripts\python.exe"
$logDir  = Join-Path $PSScriptRoot "logs"
$port    = 8400        # NOTE: 8000 is reserved by HTTP.sys on this machine
$interval = 300                                        # seconds between agent cycles

if (-not (Test-Path $python))  { Write-Error "Python venv not found: $python"; exit 1 }
if (-not (Test-Path $crawler)) { Write-Error "super_crawler not found: $crawler"; exit 1 }
New-Item -ItemType Directory -Force $logDir | Out-Null
New-Item -ItemType Directory -Force (Join-Path $crawler "data\reddit_inbox") | Out-Null

# Single-instance guard: if the dashboard already answers, do not start a second copy.
try {
    $alive = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/runtime" -UseBasicParsing -TimeoutSec 3
    if ($alive.StatusCode -eq 200) { Write-Output "Agent already running on port $port. Exiting."; exit 0 }
} catch { }  # not running -> proceed

while ($true) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $out = Join-Path $logDir "agent-$stamp.out.log"
    $err = Join-Path $logDir "agent-$stamp.err.log"
    Write-Output "[$stamp] starting super_crawler agent on port $port (logs: $out)"
    $proc = Start-Process -FilePath $python `
        -ArgumentList "-m", "super_crawler.cli", "serve", "--host", "127.0.0.1", "--port", "$port", "--interval-seconds", "$interval", "--autostart" `
        -WorkingDirectory $crawler -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError $err
    $proc.WaitForExit()
    $code = $proc.ExitCode
    Write-Output "[$(Get-Date -Format 'yyyyMMdd-HHmmss')] agent exited with code $code; restarting in 5s"
    Start-Sleep -Seconds 5
}
