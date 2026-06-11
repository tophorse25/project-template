# Registers the agent to start automatically at user logon (survives reboots).
# Tries a Task Scheduler logon task first; falls back to a Startup-folder entry
# (which never needs elevation). Re-run safe.
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File register_startup.ps1

$launcher = Join-Path $PSScriptRoot "start_super_crawler.ps1"
$command  = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""

schtasks /Create /TN "SuperCrawlerAgent" /TR "$command" /SC ONLOGON /F 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Output "Registered Task Scheduler logon task: SuperCrawlerAgent"
} else {
    $startup = [Environment]::GetFolderPath("Startup")
    $cmdPath = Join-Path $startup "SuperCrawlerAgent.cmd"
    "@echo off`r`nstart `"SuperCrawlerAgent`" /min $command" | Out-File -FilePath $cmdPath -Encoding ascii
    Write-Output "Task Scheduler unavailable; registered Startup-folder entry: $cmdPath"
}
Write-Output "The agent will start at next logon. To start it NOW, run start_super_crawler.ps1 (or log off/on)."
