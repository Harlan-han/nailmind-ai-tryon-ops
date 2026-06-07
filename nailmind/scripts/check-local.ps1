param(
  [string]$Backend = "http://localhost:8004",
  [string]$Frontend = "http://localhost:3000",
  [switch]$InProcessBackend,
  [int]$InProcessPort = 8124
)

$ErrorActionPreference = "Continue"

function Test-Endpoint($Name, $Method, $Url, $Body = $null, $Headers = $null) {
  Write-Host "Checking $Name..." -ForegroundColor Cyan
  try {
    if ($Body) {
      if ($Headers) {
        $response = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Url -ContentType "application/json" -Body $Body -Headers $Headers -TimeoutSec 8
      } else {
        $response = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Url -ContentType "application/json" -Body $Body -TimeoutSec 8
      }
    } else {
      if ($Headers) {
        $response = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Url -Headers $Headers -TimeoutSec 8
      } else {
        $response = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Url -TimeoutSec 8
      }
    }
    Write-Host "  OK $($response.StatusCode)" -ForegroundColor Green
    return @{
      Ok = $true
      Response = $response
    }
  } catch {
    if ($_.Exception.Response) {
      $statusCode = [int]$_.Exception.Response.StatusCode
      Write-Host "  FAIL $statusCode" -ForegroundColor Red
    } else {
      Write-Host "  FAIL $($_.Exception.Message)" -ForegroundColor Red
    }
    return @{
      Ok = $false
      Response = $null
    }
  }
}

$authBody = '{"phone":"13910000001","nickname":"Harlan","user_type":"consumer"}'
$webhookBody = '{"channel":"feishu","sender":"local_check","text":"生成今日运营日报"}'

$results = @()
$frontendCheck = Test-Endpoint "frontend" "GET" $Frontend
$results += $frontendCheck.Ok

if ($InProcessBackend) {
  Write-Host "Checking backend in-process Uvicorn HTTP server..." -ForegroundColor Cyan
  $repoRoot = Split-Path -Parent $PSScriptRoot
  $backendDir = Join-Path $repoRoot "backend"
  $codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  $sitePackages = Join-Path $backendDir "venv\Lib\site-packages"
  $script = @'
import os
import threading
import time

import httpx
import uvicorn

PORT = int(os.environ.get("NAILMIND_CHECK_PORT", "8124"))
BASE_URL = f"http://127.0.0.1:{PORT}"

config = uvicorn.Config(
    "app.main:app",
    host="127.0.0.1",
    port=PORT,
    log_level="warning",
    lifespan="off",
)
server = uvicorn.Server(config)
thread = threading.Thread(target=server.run, daemon=True)
thread.start()

for _ in range(60):
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=1.0)
        if response.status_code == 200:
            break
    except Exception:
        time.sleep(0.2)
else:
    raise RuntimeError("Timed out waiting for in-process Uvicorn server")

def expect(name, response):
    print(f"{name}: {response.status_code}")
    if response.status_code >= 400:
        print(response.text[:500])
    assert response.status_code < 400, name
    return response

client = httpx.Client(base_url=BASE_URL, timeout=20.0)

expect("backend health", client.get("/health"))
consumer_code = expect("consumer login code", client.post("/api/auth/request-code", json={
    "phone": "13910000001",
    "nickname": "Harlan",
    "user_type": "consumer",
})).json()["debug_code"]
consumer_login = expect("consumer login", client.post("/api/auth/login", json={
    "phone": "13910000001",
    "code": consumer_code,
    "nickname": "Harlan",
    "user_type": "consumer",
})).json()
assert consumer_login.get("access_token")

admin_code = expect("admin login code", client.post("/api/auth/request-code", json={
    "phone": "13918889999",
    "nickname": "运营测试账号",
    "user_type": "admin",
})).json()["debug_code"]
admin_login = expect("admin login", client.post("/api/auth/login", json={
    "phone": "13918889999",
    "code": admin_code,
    "nickname": "运营测试账号",
    "user_type": "admin",
})).json()
headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
capabilities = expect("operations agent capabilities", client.get("/api/operations/assistant/capabilities", headers=headers)).json()
assert capabilities.get("version") == "agent-v2"
status = expect("operations agent status", client.get("/api/operations/assistant/status", headers=headers)).json()
assert "llm_configured" in status["runtime"]
print(f"operations agent llm configured: {status['runtime']['llm_configured']}")
expect("operations agent external webhook", client.post("/api/operations/assistant/webhook", json={
    "channel": "feishu",
    "sender": "local_check",
    "text": "生成今日运营日报",
}))
server.should_exit = True
thread.join(timeout=5)
print("in-process HTTP backend OK")
'@
  $env:PYTHONPATH = $sitePackages
  $env:NAILMIND_CHECK_PORT = [string]$InProcessPort
  Push-Location $backendDir
  try {
    $script | & $codexPython -
    $results += $LASTEXITCODE -eq 0
  } finally {
    Pop-Location
  }
} else {
$backendHealth = Test-Endpoint "backend health" "GET" "$Backend/health"
$results += $backendHealth.Ok

$consumerCode = Test-Endpoint "consumer login code" "POST" "$Backend/api/auth/request-code" $authBody
$results += $consumerCode.Ok

$adminHeaders = $null
$adminCodeBody = '{"phone":"13918889999","nickname":"Operations Check","user_type":"admin"}'
$adminCode = Test-Endpoint "admin login code" "POST" "$Backend/api/auth/request-code" $adminCodeBody
$results += $adminCode.Ok
if ($adminCode.Ok) {
  try {
    $adminCodePayload = $adminCode.Response.Content | ConvertFrom-Json
    $adminLoginBody = @{
      phone = "13918889999"
      nickname = "Operations Check"
      user_type = "admin"
      code = $adminCodePayload.debug_code
    } | ConvertTo-Json -Compress
    $adminLogin = Test-Endpoint "admin login" "POST" "$Backend/api/auth/login" $adminLoginBody
    $results += $adminLogin.Ok
    if ($adminLogin.Ok) {
      $adminLoginPayload = $adminLogin.Response.Content | ConvertFrom-Json
      $adminHeaders = @{ Authorization = "Bearer $($adminLoginPayload.access_token)" }
    }
  } catch {
    Write-Host "  FAIL admin auth parsing $($_.Exception.Message)" -ForegroundColor Red
    $results += $false
  }
}

if ($adminHeaders) {
  $capabilities = Test-Endpoint "operations agent capabilities" "GET" "$Backend/api/operations/assistant/capabilities" $null $adminHeaders
  $results += $capabilities.Ok
  $agentStatus = Test-Endpoint "operations agent status" "GET" "$Backend/api/operations/assistant/status" $null $adminHeaders
  $results += $agentStatus.Ok
  if ($agentStatus.Ok) {
    try {
      $agentStatusPayload = $agentStatus.Response.Content | ConvertFrom-Json
      Write-Host "  DeepSeek configured: $($agentStatusPayload.runtime.llm_configured)" -ForegroundColor Cyan
    } catch {
      Write-Host "  WARN could not parse operations agent status" -ForegroundColor Yellow
    }
  }
} else {
  Write-Host "Checking operations agent capabilities..." -ForegroundColor Cyan
  Write-Host "  FAIL admin token unavailable" -ForegroundColor Red
  $results += $false
  Write-Host "Checking operations agent status..." -ForegroundColor Cyan
  Write-Host "  FAIL admin token unavailable" -ForegroundColor Red
  $results += $false
}

$webhookCheck = Test-Endpoint "operations agent external webhook" "POST" "$Backend/api/operations/assistant/webhook" $webhookBody
$results += $webhookCheck.Ok
}

$passed = ($results | Where-Object { $_ }).Count
$total = $results.Count
Write-Host ""
Write-Host "Local check: $passed / $total passed"

if ($passed -ne $total) {
  Write-Host "If auth/capabilities/webhook are 404, backend 8004 is still running old code." -ForegroundColor Yellow
  exit 1
}
