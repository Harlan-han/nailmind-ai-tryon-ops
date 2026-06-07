param(
  [switch]$DeepSeekOnly,
  [switch]$RunningHubOnly
)

$ErrorActionPreference = "Stop"

function Set-UserSecret($Name, $Prompt) {
  $secureValue = Read-Host $Prompt -AsSecureString
  $plainValue = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
  )
  if ([string]::IsNullOrWhiteSpace($plainValue)) {
    Write-Host "$Name skipped: empty value" -ForegroundColor Yellow
    return
  }

  [Environment]::SetEnvironmentVariable($Name, $plainValue, "User")
  [Environment]::SetEnvironmentVariable($Name, $plainValue, "Process")
  Write-Host "$Name configured for the current Windows user" -ForegroundColor Green
}

if (-not $RunningHubOnly) {
  Set-UserSecret "DEEPSEEK_API_KEY" "Enter DeepSeek API Key"
}

if (-not $DeepSeekOnly) {
  Set-UserSecret "RUNNINGHUB_API_KEY" "Enter RunningHub API Key"
}

Write-Host ""
Write-Host "Restart local services with: powershell -ExecutionPolicy Bypass -File nailmind\scripts\start-local.ps1"
