param([Parameter(Mandatory=$true)][string]$Destino)
$ErrorActionPreference = 'Stop'
$Origen = Split-Path -Parent $MyInvocation.MyCommand.Path
$destPath = [System.IO.Path]::GetFullPath($Destino)
if (-not (Test-Path -LiteralPath (Join-Path $destPath 'run.py'))) { throw "Destino invalido: selecciona la carpeta que contiene run.py" }
if (-not (Test-Path -LiteralPath (Join-Path $Origen 'app'))) { throw "Falta app en el paquete descomprimido" }
if ($destPath.TrimEnd('\') -eq [System.IO.Path]::GetFullPath($Origen).TrimEnd('\')) { throw 'Descomprime el paquete en otra carpeta; no se puede instalar sobre la misma ruta de origen.' }
$fecha = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path (Split-Path $destPath -Parent) ("RESPALDO_V9_ANTES_DE_SISTEMAS_" + $fecha)
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Write-Host "Creando copia de app y config en $backup"
Copy-Item -LiteralPath (Join-Path $destPath 'app') -Destination (Join-Path $backup 'app') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $destPath 'config.py') -Destination $backup -Force
Write-Host 'Copiando carpetas de codigo y recursos; sin borrar la app anterior...'
Copy-Item -Path (Join-Path $Origen 'app\*') -Destination (Join-Path $destPath 'app') -Recurse -Force
foreach ($nombre in @('config.py','inicializar_catalogo_sistemas.py','verificar_nexo_sistemas.py','LEEME_PRIMERO_SISTEMAS_V10.md')) {
    Copy-Item -LiteralPath (Join-Path $Origen $nombre) -Destination (Join-Path $destPath $nombre) -Force
}
Write-Host 'Actualizacion copiada correctamente.' -ForegroundColor Green
Write-Host 'La BD, .env, .venv, cuentas y archivos subidos NO fueron modificados por el instalador.'
Write-Host "Respaldo anterior: $backup"
Write-Host 'Siguiente: ejecutar verificar_nexo_sistemas.py y preparar catalogo 17A4SI con anio oficial.'
