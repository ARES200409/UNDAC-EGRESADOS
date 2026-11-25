# Ejecutar desde carpeta NEXO_UNDAC_V9: .\iniciar_demo_celular.ps1 -IpLocal 192.168.1.105
param([Parameter(Mandatory=$true)][string]$IpLocal)
$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($IpLocal -notmatch '^(\d{1,3}\.){3}\d{1,3}$') { throw 'Introduce tu IPv4 local, consultando ipconfig.' }
if (-not (Test-Path '.\.venv\Scripts\waitress-serve.exe')) { throw 'Instala waitress en el .venv del proyecto.' }
Write-Host ('URL celular, en la misma Wi-Fi: http://'+$IpLocal+':5000') -ForegroundColor Cyan
Write-Host 'Solo para una demostración local confiable. Usa cuentas demo y no publiques el puerto en internet.' -ForegroundColor Yellow
& '.\.venv\Scripts\waitress-serve.exe' "--listen=${IpLocal}:5000" '--threads=4' 'wsgi:app'
