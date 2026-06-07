param(
  [string]$Backend = "http://localhost:8004",
  [string]$Frontend = "http://localhost:3000",
  [string]$AiService = "http://localhost:8003"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "acceptance_e2e.py"
$projectPython = Join-Path (Split-Path -Parent $scriptDir) "backend\venv\Scripts\python.exe"

if (Test-Path $projectPython) {
  & $projectPython $pythonScript --backend $Backend --frontend $Frontend --ai-service $AiService
} else {
  python $pythonScript --backend $Backend --frontend $Frontend --ai-service $AiService
}
