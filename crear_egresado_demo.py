"""
Script para crear un egresado de demostración completo.
Uso: .\.venv\Scripts\python.exe crear_egresado_demo.py

NO afecta la API ni datos existentes. Inserta directamente en la BD local.
Puede ejecutarse varias veces: si el egresado ya existe, lo informa y sale.
"""

from datetime import date, datetime
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Egresados, Usuarios, UsuarioRoles, Roles,
    Empleos, TrayectoriaAcademica, Certificados, Habilidades
)

# ── Datos del egresado de prueba ──────────────────────────────
DNI_DEMO            = "70000001"
CORREO_DEMO         = "carlos.quispe.demo@undac.edu.pe"
PASSWORD_DEMO       = "Demo2026undac!"
COD_UNIVERSITARIO   = "2019S0001"

DATOS_EGRESADO = dict(
    dni                  = DNI_DEMO,
    codigo_universitario = COD_UNIVERSITARIO,
    apellido_paterno     = "QUISPE",
    apellido_materno     = "HUAMAN",
    nombres              = "Carlos Andrés",
    genero               = "M",
    fecha_nacimiento     = date(1998, 3, 15),
    correo_institucional = CORREO_DEMO,
    correo_personal      = "carlos.quispe.demo@gmail.com",
    telefono             = "963852741",
    domicilio            = "Jr. Bolognesi 456",
    distrito             = "Yanacancha",
    provincia            = "Pasco",
    region               = "Pasco",
    pais                 = "Perú",
    linkedin             = "https://linkedin.com/in/carlos-quispe-demo",
    titulo_cv            = "Ingeniero de Sistemas | Desarrollador Full Stack",
    perfil_profesional   = (
        "Egresado de Ingeniería de Sistemas y Computación de la UNDAC. "
        "Experiencia en desarrollo de aplicaciones web con Python, Flask y MySQL. "
        "Conocimientos en administración de bases de datos, análisis de datos "
        "y metodologías ágiles. Comprometido con la innovación tecnológica "
        "al servicio de la región Pasco."
    ),
    anio_ingreso         = 2019,
    periodo              = "2019-I",
    anio_egreso          = 2024,
    es_bachiller         = 1,
    es_titulado          = 1,
    tiene_maestria       = 0,
    tiene_doctorado      = 0,
    tiene_phd            = 0,
    nivel_maximo         = "titulado",
)

# ── Datos complementarios ─────────────────────────────────────
TRAYECTORIA = [
    dict(
        tipo            = "bachiller",
        grado_titulo    = "Bachiller en Ingeniería de Sistemas y Computación",
        institucion     = "Universidad Nacional Daniel Alcides Carrión",
        fecha_obtencion = date(2024, 7, 15),
        fuente          = "autodeclarado",
    ),
    dict(
        tipo            = "titulado",
        grado_titulo    = "Ingeniero de Sistemas y Computación",
        institucion     = "Universidad Nacional Daniel Alcides Carrión",
        fecha_obtencion = date(2024, 12, 20),
        fuente          = "autodeclarado",
    ),
]

CERTIFICADOS = [
    dict(
        nombre              = "Python Full Stack Developer",
        institucion_emisora = "Platzi",
        tipo                = "externo",
        categoria           = "curso",
        fecha_emision       = date(2024, 5, 10),
    ),
    dict(
        nombre              = "Scrum Fundamentals Certified (SFC)",
        institucion_emisora = "SCRUMstudy",
        tipo                = "externo",
        categoria           = "capacitacion",
        fecha_emision       = date(2024, 8, 22),
    ),
    dict(
        nombre              = "Inglés",
        institucion_emisora = "Centro de Idiomas UNDAC",
        tipo                = "interno",
        categoria           = "idioma",
        nivel_idioma        = "intermedio",
        fecha_emision       = date(2023, 12, 15),
    ),
    dict(
        nombre              = "Análisis de Datos con Power BI",
        institucion_emisora = "Microsoft Learn",
        tipo                = "externo",
        categoria           = "capacitacion",
        fecha_emision       = date(2025, 2, 10),
    ),
]

HABILIDADES = [
    ("Python",              "habilidad"),
    ("Flask / Django",      "habilidad"),
    ("MySQL / PostgreSQL",  "habilidad"),
    ("JavaScript",          "habilidad"),
    ("Git / GitHub",        "habilidad"),
    ("Power BI",            "habilidad"),
    ("Scrum / Agile",       "habilidad"),
    ("Desarrollo web",      "interes"),
    ("Inteligencia Artificial", "interes"),
    ("Ciberseguridad",      "interes"),
]


def main():
    app = create_app()
    with app.app_context():
        # Comprobar si ya existe
        existente = Egresados.query.filter_by(dni=DNI_DEMO).first()
        if existente:
            print(f"⚠  El egresado demo (DNI {DNI_DEMO}) ya existe (ID {existente.id_egresado}).")
            u = Usuarios.query.filter_by(correo=CORREO_DEMO).first()
            if u:
                print(f"   Login: {CORREO_DEMO} / {PASSWORD_DEMO}")
            return

        # ── 1. Buscar currícula 17A4SI de Sistemas ────────────
        from app.models import Curriculas
        curricula = Curriculas.query.filter_by(nombre="17A4SI").first()
        if not curricula:
            print("❌ No se encontró la currícula 17A4SI. Ejecuta primero inicializar_catalogo_sistemas.py")
            return

        # ── 2. Crear el egresado ──────────────────────────────
        egresado = Egresados(id_curricula=curricula.id_curricula, **DATOS_EGRESADO)
        db.session.add(egresado)
        db.session.flush()  # obtener id_egresado
        print(f"✔  Egresado creado: {egresado.nombre_completo()} (ID {egresado.id_egresado})")

        # ── 3. Crear usuario con login ────────────────────────
        hash_pw = bcrypt.generate_password_hash(PASSWORD_DEMO).decode("utf-8")
        usuario = Usuarios(
            correo          = CORREO_DEMO,
            contrasena_hash = hash_pw,
            id_egresado     = egresado.id_egresado,
            estado          = "activo",
        )
        db.session.add(usuario)
        db.session.flush()

        # Asignar rol "egresado"
        rol_egresado = Roles.query.filter_by(nombre="egresado").first()
        db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=rol_egresado.id_rol))
        print(f"✔  Usuario creado: {CORREO_DEMO}")

        # ── 4. Empleo actual ──────────────────────────────────
        empleo = Empleos(
            id_egresado  = egresado.id_egresado,
            id_empresa   = 1,  # [DEMO] Organización Tecnología Pasco
            cargo        = "Desarrollador de Software",
            tipo_contrato = "Contrato a plazo fijo",
            funciones    = (
                "Desarrollo de aplicaciones web con Python y Flask. "
                "Gestión de bases de datos MySQL. "
                "Implementación de APIs REST. "
                "Soporte técnico y mantenimiento de sistemas internos."
            ),
            fecha_inicio = date(2025, 3, 1),
            fecha_fin    = None,
            es_actual    = 1,
        )
        db.session.add(empleo)
        print("✔  Empleo actual registrado")

        # ── 5. Trayectoria académica ──────────────────────────
        for t in TRAYECTORIA:
            db.session.add(TrayectoriaAcademica(id_egresado=egresado.id_egresado, **t))
        print(f"✔  Trayectoria académica: {len(TRAYECTORIA)} registros")

        # ── 6. Certificados ──────────────────────────────────
        for c in CERTIFICADOS:
            db.session.add(Certificados(id_egresado=egresado.id_egresado, **c))
        print(f"✔  Certificados: {len(CERTIFICADOS)} registros")

        # ── 7. Habilidades e intereses ────────────────────────
        for nombre, tipo in HABILIDADES:
            db.session.add(Habilidades(id_egresado=egresado.id_egresado, nombre=nombre, tipo=tipo))
        print(f"✔  Habilidades e intereses: {len(HABILIDADES)} registros")

        # ── Confirmar todo ────────────────────────────────────
        db.session.commit()

        print()
        print("=" * 60)
        print("  EGRESADO DE DEMOSTRACIÓN CREADO EXITOSAMENTE")
        print("=" * 60)
        print(f"  Nombre:   {egresado.nombre_completo()}")
        print(f"  DNI:      {DNI_DEMO}")
        print(f"  Programa: Ingeniería de Sistemas y Computación")
        print(f"  Nivel:    Titulado")
        print(f"  Empleo:   Desarrollador de Software (actual)")
        print(f"  Certif.:  {len(CERTIFICADOS)} certificados")
        print(f"  Skills:   {len(HABILIDADES)} habilidades/intereses")
        print("=" * 60)
        print(f"  🔑 LOGIN:")
        print(f"     Correo:     {CORREO_DEMO}")
        print(f"     Contraseña: {PASSWORD_DEMO}")
        print("=" * 60)


if __name__ == "__main__":
    main()
