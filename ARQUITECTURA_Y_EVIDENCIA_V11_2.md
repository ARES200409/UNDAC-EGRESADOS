# NEXO UNDAC V11.2 · Arquitectura y evidencia de ingeniería

## Objetivo
Sistema de seguimiento de egresados de Ingeniería de Sistemas y Computación de la UNDAC. Arquitectura web modular monolítica (Flask) con MySQL. No hay microservicios ficticios ni IA que decida empleabilidad.

## Stack implementado en el proyecto

| Capa | Herramientas | Evidencia verificable |
|---|---|---|
| Backend | Python 3.12 / Flask / blueprints | `app/__init__.py`, directorios de roles |
| Persistencia | MySQL / SQLAlchemy / PyMySQL | `config.py`, `app/models.py`, `verificar_ingenieria_v11_2.py` |
| Frontend | HTML, Jinja, CSS, JS, Bootstrap | `app/templates`, `app/static` |
| Interactividad | HTMX con ruta convencional alternativa | módulo padrón |
| Visualización | Apache ECharts; SVG alternativo | `app/static/js/v11_indicadores.js` |
| Seguridad existente | sesiones, roles, CSRF, bcrypt | Flask-Login, Flask-WTF y rutas |
| Documentos | ReportLab, OpenPyXL | generadores PDF y Excel |
| Operación nueva | Waitress WSGI, endpoints live/ready | `wsgi.py`, `/health/live`, `/health/ready` |
| Observabilidad nueva | ID por solicitud, logs JSON sin datos personales | `app/observabilidad_v11_2.py` |
| QA y CI | pytest/SQLite, diagnósticos, GitHub Actions | `tests`, `.github/workflows/calidad.yml` |

## Arquitectura en una línea

Usuario → navegador HTML + HTMX + ECharts → Flask / Blueprints / autorización → SQLAlchemy → MySQL.

Los PDF y las notificaciones son funcionalidades locales existentes; no hay un backend Next.js ni una API de empleos en tiempo real integrada.

## Qué comprobar delante del docente

1. Inicia sesión en roles distintos; el menú y los datos visibles deben ajustarse a cada rol.
2. En Administrador/UTSAG/Coordinador/Docente muestra el mismo padrón con ámbitos y métricas ajustadas, no porcentajes inventados.
3. En Egresado consulta perfil, CV, encuestas y oportunidades.
4. Visita `/health/live`: proceso vivo; `/health/ready`: consulta SELECT 1 real de MySQL.
5. `verificar_ingenieria_v11_2.py` muestra conexión, tablas y acceso sin sesión denegado.
6. Ejecuta `python -m pytest -q tests` para verificar que la suite no escriba en MySQL real.
7. Enseña `.github/workflows/calidad.yml`, automatización *configurada*; **NO afirmes que ya corrió en GitHub si no hiciste push.**

## Lo que NO está acreditado

- Ni seguridad certificada ni auditoría de penetración OWASP ASVS completa.
- Ni pruebas de carga de cientos de usuarios simultáneos.
- Ni Docker desplegado ni CI ejecutado en GitHub si no se ha comprobado externamente.
- Ni IA de recomendación, integraciones de empleos externos en vivo, SUNEDU API, AWS ni microservicios.
- Ni fecha oficial de inicio de currícula 17A4SI; el año de ingreso de una persona no es el año del plan.
- Ni cobertura universitaria real con 1 de 1 egresados locales.

**Conclusión:** V11.2 agrega observabilidad, monitorización, operación WSGI y automatización verificables. Siguen siendo necesarias pruebas de seguridad, restauración de copias, roles en vivo y despliegue HTTPS para producción pública.
