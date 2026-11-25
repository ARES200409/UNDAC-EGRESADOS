"""Motor local de guías verificadas, sin llamadas a APIs externas ni datos privados."""
import re
import unicodedata

def normalizar(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(s or '').casefold())
                            if not unicodedata.combining(c)).split())

# Las rutas corresponden a los módulos ya visibles del piloto Sistemas.
# Evitar afirmar cosas que no estén verificadas por el usuario/administrador.
GUIA = [
    ({'iniciar sesion','ingresar','acceder','login','entrar'},
     'GUÍA PARA INICIAR SESIÓN\n1. Abre la página principal de NEXO UNDAC.\n2. Selecciona «Ingresar».\n3. Escribe tus credenciales en el formulario seguro.\n4. Selecciona el rol que tengas autorizado y accede.\nConsejo: nunca compartas contraseñas en este chat.'),
    ({'registr','crea cuenta','codigo universitario','verificar identidad','nueva cuenta'},
     'GUÍA PARA REGISTRARTE\n1. En la portada elige «Soy egresado».\n2. Ingresa tu código universitario y DNI únicamente en el formulario oficial, NO en el chat.\n3. Pulsa «Verificar identidad».\n4. Comprueba que tu programa académico coincida con Ingeniería de Sistemas y Computación.\n5. Continúa para crear la cuenta siguiendo las indicaciones de pantalla.\nSi el sistema no reconoce el plan, comunícate con el administrador.'),
    ({'curricula','plan de estudios','17a4si'},
     'INFORMACIÓN CURRICULAR\n1. Abre la sección académica correspondiente.\n2. Comprueba el código curricular indicado en tu ficha.\n3. Si aparece 17A4SI, ten en cuenta que se observó ese código para Sistemas.\n4. Solicita al responsable académico que confirme el año oficial de inicio, pendiente de confirmación.\nNo deduzcas el año del plan a partir del año de ingreso.'),
    ({'rol','administrador','utsag','coordinador','docente responsable'},
     'GUÍA DE ROLES\n1. Administrador: administra cuentas, permisos y catálogo académico.\n2. UTSAG: revisa cobertura, encuestas e indicadores de seguimiento.\n3. Coordinador: consulta resultados de su facultad asignada.\n4. Docente responsable: acompaña a egresados de los programas asignados.\n5. Egresado: actualiza perfil y trayectoria, consulta ofertas y responde encuestas.\nCada opción depende de los permisos efectivos de tu cuenta.'),
    ({'encuesta','responder encuesta','participacion'},
     'GUÍA DE ENCUESTAS\n1. Inicia sesión en NEXO UNDAC.\n2. Entra en «Encuestas».\n3. Abre una encuesta disponible y pulsa «Responder».\n4. Completa las preguntas que correspondan.\n5. Revisa tus respuestas y envíalas.\nEl personal autorizado puede revisar resultados desde su propio panel.'),
    ({'mi cv','curriculum','hoja de vida','generar cv'},
     'GUÍA PARA GENERAR TU CV\n1. Inicia sesión como egresado.\n2. Abre «Mi perfil» y completa la información que desees incluir.\n3. Registra tu formación, empleos y certificados disponibles.\n4. Entra a «Mi CV» y selecciona los registros relevantes.\n5. Pulsa «Generar y descargar CV» para obtener tu PDF.\nConsejo: no inventes experiencia ni títulos.'),
    ({'certificado','capacitacion','curso','especializacion'},
     'GUÍA PARA REGISTRAR CERTIFICADOS\n1. Accede como egresado y selecciona «Certificados».\n2. Pulsa «Agregar certificado».\n3. Registra el curso, la entidad y la información comprobable solicitada.\n4. Agrega un enlace de verificación si cuentas con él.\n5. Guarda y revisa que se muestre correctamente.\nUna declaración no equivale a una verificación institucional.'),
    ({'empleo','trabajo','experiencia laboral','empresa'},
     'GUÍA PARA REGISTRAR TU EMPLEO\n1. Inicia sesión como egresado.\n2. Selecciona «Empleo».\n3. Pulsa «Registrar empleo».\n4. Completa el puesto, la organización y las fechas que conozcas.\n5. Guarda y revisa la ficha registrada.\nLa información es autodeclarada y no confirma contratación por la empresa.'),
    ({'postulacion','postular','oferta','vacante','bolsa laboral'},
     'GUÍA PARA BUSCAR Y SEGUIR OFERTAS\n1. Abre «Ofertas laborales».\n2. Filtra por puesto, competencia o ciudad.\n3. Revisa requisitos y fechas antes de continuar.\n4. En ofertas internas, utiliza «Registrar postulación»; en enlaces externos, realiza la postulación en el portal original.\n5. Consulta «Mis postulaciones» para revisar o actualizar tus avances.\nAbrir un enlace no equivale a postular ni a obtener empleo.'),
    ({'indicador','kpi','grafico','observatorio','dashboard','empleabilidad'},
     'GUÍA PARA INTERPRETAR INDICADORES\n1. Inicia sesión con un rol autorizado.\n2. Abre el observatorio o la sección «Indicadores».\n3. Consulta el período, programa y alcance indicados en la pantalla.\n4. Distingue cobertura de cuentas, respuestas a encuestas y empleo autodeclarado.\n5. No presentes esos datos como tasas oficiales ni contrataciones verificadas.\nLos gráficos utilizan registros de MySQL y dependen de los datos disponibles.'),
    ({'perfil','foto','editar datos','contacto'},
     'GUÍA PARA COMPLETAR TU PERFIL\n1. Entra con tu cuenta de egresado.\n2. Abre «Mi perfil».\n3. Pulsa «Editar perfil».\n4. Actualiza los campos permitidos y guarda.\n5. Verifica que la información aparezca correctamente.\nLos datos académicos oficiales deben conservar su origen de verificación.'),
    ({'nexo undac','plataforma','seguimiento de egresados','sistema nexo'},
     '¿QUÉ ES NEXO UNDAC?\n1. Es una plataforma de seguimiento de egresados de Ingeniería de Sistemas y Computación.\n2. Permite gestionar perfil profesional, trayectoria, encuestas y oportunidades.\n3. Cuenta con vistas diferenciadas por rol.\n4. Los indicadores muestran información registrada en el sistema, no cifras oficiales de toda la universidad.'),
    ({'saludo','hola','buenas','ayuda'},
     '¡Hola! Soy NEXO Asistente. Para ayudarte paso a paso, pregunta: «¿Cómo me registro?», «¿Cómo genero mi CV?», «¿Cómo postulo a ofertas?» o «¿Qué hace el Coordinador?».')
]

PRIVADO=('contraseña','contrasena','dni de','datos personales de','password','token de',
         'clave de','correo de otra persona','direccion de','telefono de')

def responder_guia(pregunta,rol='publico'):
    s=normalizar(pregunta)
    if not s: return 'Escribe una pregunta breve sobre NEXO UNDAC.', 'ayuda'
    if any(normalizar(v) in s for v in PRIVADO) or re.search(r'(?<!\d)\d{8}(?!\d)',s) or re.search(r'\b(?:AIza|AQ\.)[A-Za-z0-9_-]{16,}',pregunta):
        return ('No compartas DNI, contraseñas, claves de API ni información privada en el chat. '
                'El asistente no consulta expedientes personales.'),'privacidad'
    for triggers,respuesta in GUIA:
        if any(normalizar(t) in s for t in triggers):
            return respuesta,'guia'
    return ('Puedo guiarte paso a paso sobre registro, inicio de sesión, CV, perfil, '
            'certificados, empleo, ofertas, encuestas, roles e indicadores de NEXO UNDAC. '
            'Si necesitas datos de un expediente, contacta al personal autorizado.'),'sin_coincidencia'

# La IA solamente recibe un identificador de tema, no el mensaje original del usuario.
_TEMAS_APROBADOS = (
    'acceso', 'registro', 'curricula', 'roles', 'encuestas', 'cv',
    'certificados', 'empleo', 'ofertas', 'indicadores', 'perfil', 'presentacion',
    'saludo',
)

def identificar_tema(pregunta):
    s = normalizar(pregunta)
    for i, (disparadores, _) in enumerate(GUIA):
        if any(normalizar(t) in s for t in disparadores):
            return _TEMAS_APROBADOS[i]
    return None

# V11.5: respuestas contextuales verificadas, sin inventar nuevos procedimientos.
# Si el estudiante pide detalles de un paso, solo se reutiliza la guía publicada.
def explicar_paso(pregunta, tema_anterior):
    """Devuelve una explicación focalizada si el tema previo pertenece al catálogo.

    No accede a perfiles ni a historiales personales; no consulta ningún proveedor.
    """
    if not isinstance(pregunta, str) or not isinstance(tema_anterior, str):
        return None
    if tema_anterior not in _TEMAS_APROBADOS:
        return None
    mensaje = normalizar(pregunta)
    patron = re.search(r'\b(?:paso|punto|numero)\s*([1-5])\b', mensaje)
    if not patron:
        return None
    numero = int(patron.group(1))
    if not any(t in mensaje for t in ('explica', 'detalle', 'aclara', 'muestra', 'ver ', 'paso ', 'punto ', 'numero ')):
        return None
    indice = _TEMAS_APROBADOS.index(tema_anterior)
    fuente = GUIA[indice][1]
    pasos = {}
    for linea in fuente.splitlines():
        coincide = re.match(r'^\s*([1-5])[.)]\s+(.+)', linea)
        if coincide:
            pasos[int(coincide.group(1))] = coincide.group(2).strip()
    contenido = pasos.get(numero)
    if contenido is None:
        return (f'La guía «{tema_anterior}» no dispone del paso {numero}. '
                'Puedes pedir otro paso de la misma guía.')
    cierre = 'Este paso se basa únicamente en la guía institucional del sistema.'
    if numero + 1 in pasos:
        cierre += f' Después puedes continuar con el paso {numero + 1}.'
    return f'DETALLE DE LA GUÍA: PASO {numero}\n{numero}. {contenido}\n{cierre}'
