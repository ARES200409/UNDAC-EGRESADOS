# NEXO UNDAC · Servidor local Waitress (Windows). No abre puertos externos.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz
$python = Join-Path $raiz '.venv\Scripts\python.exe'
$waitress = Join-Path $raiz '.venv\Scripts\waitress-serve.exe'
if (-not (Test-Path $python)) { throw 'Falta .venv en este proyecto.' }
if (-not (Test-Path $waitress)) {
  Write-Host 'Waitress no esta instalado. Desde D: ejecuta:' -ForegroundColor Yellow
  Write-Host '.\.venv\Scripts\python.exe -m pip install --no-cache-dir "waitress>=3,<4"'
  exit 1
}
Write-Host 'NEXO UNDAC en http://127.0.0.1:5000 (solo esta PC)' -ForegroundColor Cyan
& $waitress --listen=127.0.0.1:5000 --threads=4 wsgi:app
exit $LASTEXITCODE
