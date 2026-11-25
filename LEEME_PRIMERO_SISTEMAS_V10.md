# NEXO UNDAC — Sistemas V10 · Guía de instalación segura

**Ámbito:** Escuela de Formación Profesional de Ingeniería de Sistemas y Computación — Facultad de Ingeniería, UNDAC.
**Tecnologías:** Python 3.12, Flask, MySQL 8, HTML/Jinja, CSS, JavaScript.
**Interfaz:** menú horizontal, azul/celeste/blanco, logos originales UNDAC y Sistemas.

## Antes de reemplazar

1. Detén Flask con Ctrl+C.
2. Mantén un respaldo de toda la carpeta del proyecto actual V9.3.
3. Mantén un respaldo SQL **actualizado** de MySQL, incluyendo triggers; el respaldo anterior de 20 tablas no incluye V8/V9.
4. No borres la BD `seguimiento_egresados` ni ejecutes scripts SQL antiguos que incluyan `DROP TABLE`.
5. No copies un `.env` de este ZIP sobre el tuyo; **este ZIP no contiene tu .env**.

## Instalación recomendada sobre tu V9.3 actual

Desde PowerShell, con el ZIP **descomprimido** y con el proyecto V9 cerrado:

```powershell
# Ejemplo. Ajusta la ruta a la carpeta donde realmente tienes la V9.
.\INSTALAR_SOBRE_V9.ps1 -Destino "D:\UNHEVAL 2026 - CURSOS\INGENIERIA EMPRESARIAL\NEXO_UNDAC_V9"
```

El instalador crea copia del `app`, luego **combina** archivos y actualiza `config.py`,
los utilitarios y la documentación. No elimina `static/uploads`, no sobrescribe `.env`,
no elimina `.venv` y no modifica MySQL.

Para evitar la política de scripts PowerShell también puedes copiar manualmente la carpeta `app` sobre tu V9,
**combinando y reemplazando** archivos sin eliminar la carpeta original. Copia además `config.py`,
`verificar_nexo_sistemas.py` e `inicializar_catalogo_sistemas.py` junto a `run.py`.

## Preparación de la currícula

Dos respuestas académicas mostradas por el usuario indican el programa
`Ingeniería de Sistemas y Computación` y el código **`17A4SI`**. El código está
observado en la API, pero **no se ha verificado el año oficial de inicio del plan**.
No lo inventaremos ni usaremos el año de ingreso de una persona.

Consulta de diagnóstico (sin cambios):

```powershell
.\.venv\Scripts\python.exe inicializar_catalogo_sistemas.py
```

Cuando confirmes el año oficial de inicio de la currícula `17A4SI`, ejecútalo así,
**sustituyendo AAAA por ese año confirmado**:

```powershell
.\.venv\Scripts\python.exe inicializar_catalogo_sistemas.py --anio-inicio AAAA
```

Este comando incorpora Facultad de Ingeniería, el programa de Sistemas y el código de
currícula solo si faltan; es idempotente y **no borra ninguna otra facultad**.

## Comprobación de instalación

```powershell
.\.venv\Scripts\python.exe verificar_nexo_sistemas.py
.\.venv\Scripts\python.exe run.py
```

Abre http://127.0.0.1:5000 y recarga Ctrl+F5.
Usa tus cuentas ya creadas. Si coordinador o docente estaban asignados a Educación,
**deberán asignarse al nuevo programa Sistemas desde administrador / Personal**.
El filtro es seguro: no les entrega acceso automático a otra escuela.

### ¿Por qué algunos indicadores se ven en cero?

La API puede devolver una coincidencia sin que la persona haya creado cuenta.
El padrón de NEXO crece cuando se termina su registro. Un campo `anio_egreso` no informado
produce un gráfico de promociones vacío; no lo sustituimos por el `anio_ingreso`.
Un egresado sin empleo declarado NO es automáticamente desempleado.

### ¿Qué rol hace qué?

- Administrador: usuarios, roles, catálogos, publicaciones y auditoría técnica.
- UTSAG: cobertura del padrón, encuestas y analítica del programa; sin permisos técnicos.
- Coordinador: programa de Sistemas y los egresados de sus asignaciones.
- Docente responsable: egresados y resultados del programa asignado.
- Egresado: perfil, empleos, estudios, habilidades, certificados, CV, encuestas y postulaciones.

La empresa no necesita cuenta: la plataforma puede enlazar fuentes laborales externas.
Las postulaciones internas se conservan; las externas son autodeclaradas.

### Limitaciones honestas

- No disponemos de tu MySQL local en este entorno; la comprobación funcional definitiva
  requiere ejecutar y probar cada rol en tu computadora.
- La descarga automática de ofertas desde portales externos requiere API/acuerdo autorizado.
- Los archivos existentes en `static/uploads` pueden requerir un plan de privacidad,
  ya que las URL estáticas no restringen lectura. No publiques datos personales reales
  hasta revisar permisos, avisos de privacidad y almacenamiento de documentos.
- Fotografías de recursos locales del proyecto; no se debe afirmar que son fotografías
  oficiales si no hay autorización o fuente verificada.

## Fuentes institucionales para la denominación

- https://sistemas.undac.edu.pe/index.php/informacion
  (identifica la Facultad de Ingeniería, 10 semestres, 220 créditos).
- La correspondencia específica de la API a `17A4SI` procede de las verificaciones realizadas por el usuario.

Version: V10 Sistemas, 16 noviembre 2026.
