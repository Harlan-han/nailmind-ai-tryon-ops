param(
  [switch]$FrontendOnly,
  [switch]$BackendOnly,
  [switch]$AiOnly,
  [int]$BackendPort = 8004,
  [int]$AiPort = 8003,
  [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Test-Port($Port) {
  $windowsDir = $env:WINDIR
  if (-not $windowsDir) {
    $windowsDir = "C:\Windows"
  }
  $netstat = Join-Path $windowsDir "System32\netstat.exe"
  $result = & $netstat -ano | Select-String "LISTENING" | Where-Object {
    $parts = ($_.ToString() -split '\s+') | Where-Object { $_ }
    $parts.Length -ge 4 -and $parts[1] -match ":$Port$"
  }
  return [bool]$result
}

function Find-Python($ServiceDir) {
  $venvPython = Join-Path $ServiceDir "venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    try {
      & $venvPython --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return @{
          Exe = $venvPython
          PythonPath = $null
        }
      }
    } catch {
      Write-Host "venv Python is not usable: $venvPython" -ForegroundColor Yellow
    }
  }

  $systemPython = Get-Command python -ErrorAction SilentlyContinue
  if ($systemPython) {
    return @{
      Exe = $systemPython.Source
      PythonPath = $null
    }
  }

  $codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  $sitePackages = Join-Path $ServiceDir "venv\Lib\site-packages"
  if ((Test-Path $codexPython) -and (Test-Path $sitePackages)) {
    try {
      & $codexPython --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return @{
          Exe = $codexPython
          PythonPath = $sitePackages
        }
      }
    } catch {
      Write-Host "Codex runtime Python is not usable: $codexPython" -ForegroundColor Yellow
    }
  }

  throw "No usable Python found. Reinstall Python 3.12 or recreate the venv before starting FastAPI services."
}

function Start-ProcessSafe($FilePath, $ArgumentList, $WorkingDirectory, $StandardOutput, $StandardError, $ExtraEnv = @{}) {
  $previousEnv = @{}
  foreach ($key in $ExtraEnv.Keys) {
    $previousEnv[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
    [Environment]::SetEnvironmentVariable($key, [string]$ExtraEnv[$key], "Process")
  }

  try {
    Start-Process `
      -FilePath $FilePath `
      -ArgumentList $ArgumentList `
      -WorkingDirectory $WorkingDirectory `
      -RedirectStandardOutput $StandardOutput `
      -RedirectStandardError $StandardError `
      -WindowStyle Hidden | Out-Null
  } finally {
    foreach ($key in $ExtraEnv.Keys) {
      [Environment]::SetEnvironmentVariable($key, $previousEnv[$key], "Process")
    }
  }
}

function Get-ConfiguredEnvironment($Names) {
  $result = @{}
  foreach ($name in $Names) {
    foreach ($scope in @("Process", "User", "Machine")) {
      $value = [Environment]::GetEnvironmentVariable($name, $scope)
      if (-not [string]::IsNullOrWhiteSpace($value)) {
        $result[$name] = $value
        break
      }
    }
  }
  return $result
}

function Start-FastApi($Name, $Dir, $Port) {
  if (Test-Port $Port) {
    Write-Host "$Name port $Port is already in use. Stop the old process before starting the current code." -ForegroundColor Yellow
    return
  }

  $python = Find-Python $Dir
  $log = Join-Path $Dir "$Name-$Port.log"
  $err = Join-Path $Dir "$Name-$Port.err.log"
  Write-Host "Starting $Name on $Port with $($python.Exe)" -ForegroundColor Cyan

  $serviceEnv = Get-ConfiguredEnvironment @(
    "AI_SERVICE_URL",
    "BACKEND_WEBHOOK_URL",
    "BACKEND_ORIGIN",
    "PUBLIC_ASSET_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "FEISHU_BOT_WEBHOOK_URL",
    "OPERATIONS_AGENT_EXTERNAL_TOKEN",
    "BACKEND_WEBHOOK_SECRET",
    "AI_WEBHOOK_SECRET",
    "NAILMIND_TRYON_PROVIDER",
    "RUNNINGHUB_API_KEY",
    "RUNNINGHUB_BASE_URL",
    "RUNNINGHUB_WORKFLOW_ID"
  )

  if ($Name -eq "backend" -and -not $serviceEnv.ContainsKey("AI_SERVICE_URL")) {
    $serviceEnv["AI_SERVICE_URL"] = "http://localhost:$AiPort"
  }

  if ($Name -eq "ai") {
    if (-not $serviceEnv.ContainsKey("BACKEND_WEBHOOK_URL")) {
      $serviceEnv["BACKEND_WEBHOOK_URL"] = "http://localhost:$BackendPort/api/tryon/webhook/result"
    }
    if (-not $serviceEnv.ContainsKey("BACKEND_ORIGIN")) {
      $serviceEnv["BACKEND_ORIGIN"] = "http://localhost:$BackendPort"
    }
  }

  if ($python.PythonPath) {
    $serviceEnv["PYTHONPATH"] = $python.PythonPath
    Start-ProcessSafe $python.Exe @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$Port") $Dir $log $err $serviceEnv | Out-Null
    return
  }

  Start-ProcessSafe $python.Exe @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$Port") $Dir $log $err $serviceEnv | Out-Null
}

function Start-Frontend($Dir, $Port) {
  if (Test-Port $Port) {
    Write-Host "Frontend port $Port is already in use." -ForegroundColor Yellow
    return
  }

  $frontendEnv = Get-ConfiguredEnvironment @(
    "NEXT_PUBLIC_BACKEND_ORIGIN",
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_AI_SERVICE_ORIGIN"
  )
  if (-not $frontendEnv.ContainsKey("NEXT_PUBLIC_BACKEND_ORIGIN")) {
    $frontendEnv["NEXT_PUBLIC_BACKEND_ORIGIN"] = "http://localhost:$BackendPort"
  }
  if (-not $frontendEnv.ContainsKey("NEXT_PUBLIC_API_BASE_URL")) {
    $frontendEnv["NEXT_PUBLIC_API_BASE_URL"] = "http://localhost:$BackendPort/api"
  }
  if (-not $frontendEnv.ContainsKey("NEXT_PUBLIC_AI_SERVICE_ORIGIN")) {
    $frontendEnv["NEXT_PUBLIC_AI_SERVICE_ORIGIN"] = "http://localhost:$AiPort"
  }

  Write-Host "Starting frontend on $Port" -ForegroundColor Cyan
  Start-ProcessSafe "npm.cmd" @("run", "dev", "--", "-p", "$Port") $Dir (Join-Path $Dir "frontend-$Port.log") (Join-Path $Dir "frontend-$Port.err.log") $frontendEnv | Out-Null
}

$backendDir = Join-Path $root "backend"
$aiDir = Join-Path $root "ai-service"
$frontendDir = Join-Path $root "frontend"

if ($FrontendOnly) {
  Start-Frontend $frontendDir $FrontendPort
  exit
}

if ($BackendOnly) {
  Start-FastApi "backend" $backendDir $BackendPort
  exit
}

if ($AiOnly) {
  Start-FastApi "ai" $aiDir $AiPort
  exit
}

Start-FastApi "backend" $backendDir $BackendPort
Start-FastApi "ai" $aiDir $AiPort
Start-Frontend $frontendDir $FrontendPort

Write-Host "Local preview:"
Write-Host "  C-end: http://localhost:$FrontendPort"
Write-Host "  B-end Chat: http://localhost:$FrontendPort/admin/assistant"
Write-Host "  Backend health: http://localhost:$BackendPort/health"
