# Registro de cambios de la versión V9

**Base:** proyecto recibido en `TRABAJO DE SEGUIMIENTO DE EGRESADO(1).rar`, con migración V8 ya aplicada por el usuario.

| Tipo | Ruta o archivo | Cambio |
|---|---|---|
| Seguridad | `app/__init__.py` | CSRF global y mensaje cuando el formulario está caducado |
| Seguridad | `app/templates/**/*.html` | Campos CSRF para formularios POST |
| Seguridad | `app/templates/egresado/editar_perfil.html` | Cabecera CSRF en AJAX |
| Permisos | `app/admin/encuestas.py` | Aislamiento de resultados por ámbito y filtrado de programas |
| Datos | `app/admin/encuestas.py` | Protección de exportación contra fórmulas Excel |
| Datos | `app/egresado/routes.py` | Validación de opciones, campos y números de encuestas |
| Privacidad | `app/egresado/routes.py` | CV solo permite datos del titular |
| Funcional | `app/templates/egresado/editar_empleo.html` | Pantalla de edición de experiencia inexistente en V8 |
| Funcional | `app/templates/egresado/empleos.html` | Botón editar empleo |
| Funcional | `app/egresado/routes.py` | Empresa y sector válidos al registrar/editar empleo |
| Trazabilidad | `app/egresado/seguimiento.py` | Enlace externo, registro de visita y actualización autodeclarada |
| Datos | `app/models.py` + SQL V9 | Tabla de seguimiento laboral externo |
| Analytics | `app/admin/empleabilidad.py` + HTML | KPI internos y externos segregados |
| Integridad | `app/admin/ofertas.py` | Solo seguimiento administrativo, sin contratación empresarial |
| UX | `app/templates/base.html` | Etiquetas por rol y navegación personalizada |
| UX | `app/templates/admin/dashboard.html` | Acciones institucionales según perfil |
| UX | `app/static/css/v9_institucional.css` | Rediseño de componentes, identidad por rol y tema oscuro |
| Operación | `config.py` | URL de BD segura para contraseñas con caracteres especiales y cookies |
| Operación | `verificar_instalacion_v9.py` | Diagnóstico local de estructura, rutas, plantillas y triggers |

## Restricciones
Sin pruebas de funcionamiento contra el MySQL real ni conexión universitaria externa no se puede declarar esta versión libre de defectos. Revisa `CHECKLIST_FUNCIONAL_ROLES_V9.md`.
