# Checklist de aceptación NEXO UNDAC V9

Marca cada prueba solo después de comprobarla con un usuario autorizado. Una prueba visual no sustituye comprobar MySQL.

## Bloque de seguridad
- [ ] Inicio de sesión válido por rol.
- [ ] Sesiones inactivas redirigen a login.
- [ ] Formularios POST sin CSRF rechazados.
- [ ] AJAX de habilidades funciona con token CSRF.
- [ ] Coordinador no ve ni exporta encuestas de programas ajenos.
- [ ] Docente no ve ni exporta datos de programas ajenos.
- [ ] Egresado A no puede incluir empleos de B en PDF CV enviando IDs manipulados.
- [ ] Ninguna credencial/`.env` ni archivo privado queda públicamente servido.

## Administrador
- [ ] Panel personalizado con acciones de gestión.
- [ ] Creación y edición de personal.
- [ ] Asignación de rol y facultad/programa.
- [ ] Catálogo académico enlazado a currículas existentes.
- [ ] Empresa con `id_sector` obligatorio.
- [ ] Oferta interna guarda registros y fecha de expiración.
- [ ] Postulación interna visible y cambio solo a `enviada`/`en_revision`.
- [ ] Exportación PDF y listados sin error.

## UTSAG
- [ ] Ve padrón y encuestas permitidas.
- [ ] KPI no confunden empleo declarado y contratación verificada.
- [ ] Sin acceso indebido a decisiones de contratación de terceros.

## Coordinador
- [ ] Dashboard muestra solo programas asignados.
- [ ] Filtrado por facultad y programa de su alcance.
- [ ] Resultados de encuestas no incluyen otras facultades al quitar filtros.
- [ ] KPI laborales externos aplican filtro de alcance incluso sin filtros de URL.

## Docente responsable
- [ ] Padrón y resultados limitados a programas asignados.
- [ ] No puede editar catálogos, personal ni ofertas fuera de sus permisos.
- [ ] No ve alumnos de otra facultad alterando IDs de URL.

## Egresado
- [ ] Registro validado con API universitaria disponible y currícula correspondiente.
- [ ] Editar perfil y cargar foto.
- [ ] Nuevo empleo; sugerir empresa con sector; editar; eliminar.
- [ ] Grados/títulos, certificados y CV propio.
- [ ] Habilidades dinámicas (agregar/eliminar).
- [ ] Guardar oferta, quitar guardada, postular internamente.
- [ ] Acceder al portal original no se cuenta como postulación.
- [ ] Mis postulaciones internas muestran estado actualizado.
- [ ] Mis postulaciones externas permiten actualizar estado voluntariamente.
- [ ] Encuestas: pregunta numérica inválida y opción ajena rechazadas.

## UX / visual
- [ ] Modo claro y oscuro funciona en cada uno de los cinco roles.
- [ ] Componentes y tablas mantienen legibilidad y contraste.
- [ ] Navegación móvil usable (scroll horizontal o adaptada).
- [ ] Teclado: foco visible y formularios accesibles.
- [ ] Datos vacíos presentan explicaciones, no gráficos falsos.
- [ ] Publicaciones de demostración `[DEMO]` claramente identificadas.

## Revisión técnica de instalación
- [ ] Respaldo actualizado de datos, estructura y triggers guardado localmente.
- [ ] `python verificar_instalacion_v9.py` devuelve 0.
- [ ] Crear/aplicar migración V9 en Workbench con cuenta autorizada.
- [ ] 23 tablas esperadas (si partiste de las 22 de V8).
- [ ] `python run.py` inicia sin errores.
- [ ] Inspección de registros/errores de Flask y de MySQL.
- [ ] Plan de restauración probado antes de producción.
