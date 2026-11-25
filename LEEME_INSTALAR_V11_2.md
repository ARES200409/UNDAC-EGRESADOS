# NEXO UNDAC Sistemas · Arranque y comprobaciones locales

## Arranque con Flask

Con MySQL en ejecución y la conexión configurada en `.env`, abre PowerShell desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe verificar_ingenieria_v11_2.py
.\.venv\Scripts\python.exe run.py
```

Abre `http://127.0.0.1:5000/health/live` y `http://127.0.0.1:5000/health/ready`. Ambos deben decir `ok` o `ready`; readiness exige MySQL. Para prueba HTTP automatizada, deja Flask encendido y, desde **otra terminal**:

```powershell
.\.venv\Scripts\python.exe smoke_http_v11_2.py
```

## Servidor WSGI moderno para Windows (opcional, recomendado para demo)

Flask `run.py` es de desarrollo. Un servidor WSGI es más representativo de un despliegue formal. **Solo en tu PC**, sin abrir tu servidor a internet:

```powershell
New-Item -ItemType Directory -Force 'D:\NEXO_TMP' | Out-Null
$env:TEMP='D:\NEXO_TMP'
$env:TMP='D:\NEXO_TMP'
$env:PIP_CACHE_DIR='D:\NEXO_TMP\pip-cache'
.\.venv\Scripts\python.exe -m pip install --no-cache-dir 'waitress>=3,<4'
.\iniciar_wsgi_v11_2.ps1
```

Primero **detén Flask**, porque ambos usan el puerto 5000. El servidor WSGI mantiene `127.0.0.1` para no exponer datos personales a la red. No asumas que HTTPS está habilitado porque use Waitress.

## Automatización con pytest (opcional)

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir pytest
.\.venv\Scripts\python.exe -m pytest -q tests
```

Si necesitas instalar pytest, usa la misma configuración `$env:TEMP` de D: anterior.

## Despliegue y entrega

- `wsgi.py` prepara despliegue WSGI; Waitress sirve la web en Windows; para acceso público requiere **HTTPS inverso**, cookies Secure, firewall y respaldos.
- `health/live` confirma que Flask atiende; `health/ready` hace `SELECT 1` para comprobar BD.
- `X-Request-ID` facilita correlacionar problemas; logs JSON registran endpoint y tiempo, nunca querystring, DNI ni correo.
- La carpeta `.github/workflows` es una configuración de GitHub Actions, **no una ejecución ya realizada**.
- Los tests con SQLite no sustituyen la prueba de relaciones MySQL, permisos por ámbito y correo real.
- Solo usa datos reales ya presentes; la API académica sigue siendo una integración existente que depende de la disponibilidad del servicio.

Para documentación técnica y evidencia, lee `ARQUITECTURA_Y_EVIDENCIA_V11_2.md`.
