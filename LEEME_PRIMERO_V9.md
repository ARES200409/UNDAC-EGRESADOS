# NEXO UNDAC V9 — Actualización integral auditada

**Universidad Nacional Daniel Alcides Carrión — Plataforma de seguimiento de egresados**

Esta entrega es **código fuente completo actualizado** sobre el proyecto recibido en RAR. No es una instalación conectada a la base de datos del usuario ni una certificación de funcionamiento en producción. **No contiene `.env`, claves, respaldo de datos personales, fotografías privadas ni entorno virtual.**

## 1. Qué se implementó realmente

- Se conserva la aplicación Flask/MySQL, las rutas anteriores, el padrón, facultades, currículas, empresas, ofertas, encuesta, personal, CV y dashboards.
- Identidad visual transversal renovada mediante `app/static/css/v9_institucional.css`: encabezados, navegación, tarjetas, formularios, acciones, contraste, responsividad y modo claro/oscuro. Acentos diferentes para administrador, UTSAG, coordinador, docente responsable y egresado. Nuevas tarjetas de acceso inmediato por función en el dashboard.
- Protección CSRF global con Flask-WTF, formularios POST tokenizados y cabeceras CSRF en solicitudes AJAX de habilidades.
- Consultas y conteos de resultados de encuestas limitados al ámbito académico autorizado; opciones y números validados al responder.
- Generador de CV limitado a registros del egresado autenticado.
- Plantilla funcional para **Editar experiencia laboral**, antes ausente, y enlace de edición desde el listado.
- Formulario de experiencia laboral con comprobación de sector económico y empresa.
- Registros académicos autodeclarados etiquetados de esa forma en código, no como verificación SUNEDU.
- Gestión interna de postulaciones: administrador/UTSAG/coordinador pueden registrar solo `enviada` o `en_revision` como seguimiento administrativo. **No pueden declarar contratación o rechazo en nombre de una empresa.**
- Nueva página **Mis postulaciones**: historial interno y seguimiento externo de la propia persona.
- Nueva función para **abrir vacantes externas**: solo redirige a enlaces HTTPS públicos, registra la visita si está disponible la migración V9, nunca marca una postulación automáticamente.
- Actualización voluntaria de resultados externos: visitado, postulado, entrevista, contratación declarada, no seleccionado y desistimiento.
- Nuevo panel institucional **Intermediación y KPI**, con conteos dentro del ámbito académico permitido y distinción expresa entre actividad y resultados autodeclarados.
- Nueva tabla `seguimiento_externo` en migración no destructiva V9.
- Verificador local `verificar_instalacion_v9.py` y consultas de solo lectura para estructura/triggers.

## 2. Antes de instalar: respaldo obligatorio

1. Detén el servidor local Flask.
2. Copia **todo tu proyecto actual** a una carpeta independiente, por ejemplo `D:\BACKUP_NEXO_UNDAC\proyecto_anterior`.
3. Genera **un nuevo backup completo MySQL** de la base actual, que ya contiene las dos tablas de V8 y tus postulaciones de prueba. Hazlo con usuario autorizado, incluyendo `--routines --events --triggers`, y guárdalo en tu disco local. **No compartas el backup de datos reales.**
4. No ejecutes el SQL antiguo `db_seguimiento_egresados_v1.22.sql` sobre la base actual: contiene `DROP DATABASE` y eliminaría toda tu información.
5. Si ya aplicaste la V8, **NO necesitas volver a ejecutar** la migración V8.

## 3. Instalación en Windows + PowerShell + VS Code

1. Descomprime `NEXO_UNDAC_V9_PROYECTO_COMPLETO.zip` en una carpeta temporal.
2. Abre la carpeta interna `NEXO_UNDAC_V9`.
3. Copia todo su contenido **sobre tu proyecto actual**, conservando el archivo `.env` original en tu laptop (el ZIP no lo incluye).
4. Activa tu entorno virtual ya instalado:

```powershell
cd "D:\UNHEVAL 2026 - CURSOS\INGENIERIA EMPRESARIAL\TRABAJO DE SEGUIMIENTO DE EGRESADO"
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

5. En MySQL Workbench con usuario autorizado (por ejemplo `root`), abre y ejecuta **solo** `migraciones/2026_11_09_v9_seguimiento.sql`.
6. Luego en la consola del proyecto ejecuta:

```powershell
python verificar_instalacion_v9.py
python run.py
```

7. Prueba: `http://127.0.0.1:5000/login` y `http://127.0.0.1:5000/`.

**No utilices `db.create_all()` ni sustituyas la base real.** No deberías importar ninguno de los backups anteriores como base nueva.

## 4. Roles: procesos y permisos

| Rol | Actividad principal | Alcance obligatorio |
|---|---|---|
| Administrador | Cuentas, catálogo académico, permisos, directorio, moderación y sistema | Institucional |
| UTSAG | Padrón, encuestas, seguimiento e indicadores | Institucional, según permisos otorgados |
| Coordinador | Padrón, indicadores y encuestas | Solo facultades/programas asignados |
| Docente responsable | Seguimiento y resultados | Solo programas asignados |
| Egresado | Perfil, empleos, formación, CV, oportunidades, encuestas y seguimiento | Solo su propia información |

**Empresa no es un rol obligatorio.** Las ofertas externas llevan al portal original; ninguna compañía tiene que registrarse en NEXO para recibir candidaturas. Las ofertas internas siguen disponibles. La universidad no debe registrar decisiones de contratación en nombre de terceros.

## 5. Qué significa cada dato laboral

- **Acceso externo:** la persona abrió una URL desde NEXO UNDAC. No implica postulación.
- **Postulado:** la persona declara haber enviado su candidatura al portal original.
- **Entrevista:** la persona declara que llegó a esa etapa.
- **Contratación reportada:** declaración de la persona; **no** verificación de la empresa ni efecto causal demostrado.
- **Sin registro laboral:** información ausente; no equivale a desempleo.
- **Postulación interna:** se guardó una solicitud en la base NEXO para una oferta sin URL externa.

Los KPI del panel V9 representan **oportunidades** con estado actual, excepto participantes externos que cuenta **egresados únicos**. No calculan una tasa de colocación oficial.

## 6. Migraciones SQL

- `migraciones/2026_11_08_v8_sin_datos.sql`: referencia de V8, **solo cuando todavía no exista** V8.
- `migraciones/2026_11_09_v9_seguimiento.sql`: crea tabla `seguimiento_externo`, con índices, llave foránea y restricción de una fila por egresado y oferta.
- `migraciones/solo_lectura_verificar_esquema.sql`: permite comprobar tablas, roles, triggers y procedimientos. No cambia datos.

**Triggers:** el respaldo de tablas proporcionado para la auditoría no incluía los triggers activos de la BD actual. Por tanto **no se alteraron triggers** y es obligatorio verificar `actualizar_nivel_egresado` y demás automatismos en el servidor MySQL local antes de dar el subsistema académico por validado.

## 7. Cómo probar cada rol (orden obligatorio)

1. Administrador: iniciar sesión, entrar a Dashboard, navegar Gestión académica y Personal, listar egresados, ver empresas y ofertas; asegurar que no puede declarar contratación de terceros.
2. UTSAG: iniciar con cuenta asignada y comprobar indicadores y encuestas institucionales.
3. Coordinador: asignar un rol real sobre una facultad, entrar y validar que los resultados de encuestas y KPI no contienen datos de otras facultades.
4. Docente: asignar programa real, comprobar que no accede a egresados o resultados fuera de sus programas.
5. Egresado: perfil -> Mi cuenta -> empleo -> editar empleo -> CV -> ofertas -> guardar/postular -> Mis postulaciones.
6. Oferta externa de prueba con URL HTTPS válida: abrir y confirmar que solo aumenta `visitas`. Luego declarar voluntariamente la postulación desde Mis postulaciones; comprobar KPI.
7. Repetir modo claro, oscuro, móvil y escritorio. Revisar formularios POST con sesión caducada.

**Importante:** la creación de usuarios institucionales y las asignaciones no están simuladas en la entrega; tendrás que utilizar cuentas de ensayo autorizadas y facultades de prueba. No compartas credenciales reales ni datos de terceros.

## 8. Lo que NO debe presentarse como terminado

- **Captación automática masiva de ofertas** desde Computrabajo, LinkedIn, Indeed, Empleos Perú u otros portales. No se integró ninguna API no autorizada ni se realizó scraping. Solo se admiten URLs externas registradas en la plataforma.
- **Confirmación automática de contrataciones**: no existe sin datos de la empresa o verificación independiente.
- **Notificaciones programadas** de seguimiento: requiere servicio de tareas y consentimiento previo.
- **Operación en producción**: pendientes pruebas con MySQL real, certificados HTTPS, backups automáticos, restauración, accesibilidad asistiva, pruebas de carga, revisión de dependencias y evaluación de protección de datos.
- **Dispositivos y navegadores**: no fue posible ejecutar aquí el servidor Flask con tu MySQL local. Se verificó sintaxis Python, compilación de plantillas, referencias URL y tokens CSRF en HTML estático.

La aplicación conserva funcionalidades de V8 y anteriores y puede necesitar cambios adicionales tras las pruebas locales. Por eso el verificador y el checklist son parte indispensable de la entrega.
