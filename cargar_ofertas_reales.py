"""
Script para poblar la plataforma con empresas y ofertas laborales reales de Perú
y simular actividad completa para el egresado de prueba Carlos Quispe.

Uso:
  .\.venv\Scripts\python.exe cargar_ofertas_reales.py
"""

from datetime import date, datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    Sectores, Empresas, OfertasLaborales, Egresados,
    OfertasGuardadas, Postulaciones, SeguimientoExterno
)

SECTORES_REALES = [
    "Tecnología y Software",
    "Minería y Metalurgia",
    "Banca y Finanzas",
    "Telecomunicaciones",
    "Consultoría y Servicios TI",
    "Sector Público y Educación"
]

EMPRESAS_REALES = [
    {
        "ruc": "20516641571",
        "razon_social": "NEXA RESOURCES PERU S.A.A.",
        "nombre_comercial": "Nexa Resources Perú",
        "sector": "Minería y Metalurgia",
        "tipo_empresa": "Gran Empresa Minera",
        "direccion": "Av. San Borja Norte 523 (U.M. El Porvenir, Pasco)",
        "distrito": "San Borja",
        "provincia": "Lima",
        "region": "Lima / Pasco",
        "telefono": "017105500",
        "sitio_web": "https://www.nexaresources.com",
    },
    {
        "ruc": "20419471018",
        "razon_social": "VOLCAN COMPAÑIA MINERA S.A.A.",
        "nombre_comercial": "Volcan Minera",
        "sector": "Minería y Metalurgia",
        "tipo_empresa": "Gran Empresa Minera",
        "direccion": "Av. Manuel Olguín 375, Surco (Unidad Cerro de Pasco)",
        "distrito": "Santiago de Surco",
        "provincia": "Lima",
        "region": "Lima / Pasco",
        "telefono": "014167000",
        "sitio_web": "https://www.volcan.com.pe",
    },
    {
        "ruc": "20100047218",
        "razon_social": "BANCO DE CREDITO DEL PERU",
        "nombre_comercial": "Banco de Crédito BCP",
        "sector": "Banca y Finanzas",
        "tipo_empresa": "Banca Múltiple",
        "direccion": "Calle Centenario 156, Urb. Las Laderas de Melgarejo",
        "distrito": "La Molina",
        "provincia": "Lima",
        "region": "Lima",
        "telefono": "013119898",
        "sitio_web": "https://www.viabcp.com",
    },
    {
        "ruc": "20600171221",
        "razon_social": "GLOBANT PERU S.A.C.",
        "nombre_comercial": "Globant Perú",
        "sector": "Tecnología y Software",
        "tipo_empresa": "Servicios de Software Globales",
        "direccion": "Av. Víctor Andrés Belaúnde 147, Torre Real 2, San Isidro",
        "distrito": "San Isidro",
        "provincia": "Lima",
        "region": "Lima",
        "telefono": "017128500",
        "sitio_web": "https://www.globant.com",
    },
    {
        "ruc": "20380312675",
        "razon_social": "NTT DATA PERU S.A.C.",
        "nombre_comercial": "NTT DATA Perú",
        "sector": "Consultoría y Servicios TI",
        "tipo_empresa": "Consultoría y Soluciones TI",
        "direccion": "Av. Faustino Sánchez Carrión 465, Torre 2",
        "distrito": "Magdalena del Mar",
        "provincia": "Lima",
        "region": "Lima",
        "telefono": "016155800",
        "sitio_web": "https://pe.nttdata.com",
    },
    {
        "ruc": "20100017491",
        "razon_social": "TELEFONICA DEL PERU S.A.A.",
        "nombre_comercial": "Telefónica / Movistar",
        "sector": "Telecomunicaciones",
        "tipo_empresa": "Telecomunicaciones",
        "direccion": "Jr. Domingo Martínez Luján 1130",
        "distrito": "Surquillo",
        "provincia": "Lima",
        "region": "Lima",
        "telefono": "012101000",
        "sitio_web": "https://www.telefonica.com.pe",
    }
]

OFERTAS_REALES = [
    {
        "empresa_ruc": "20516641571",  # Nexa
        "titulo": "Analista de Sistemas y Soporte TI en Unidad Minera",
        "modalidad": "Presencial",
        "tipo_oferta": "Tiempo completo",
        "jornada": "Régimen minero 14x7 con campamento",
        "remuneracion": "S/ 4,500 - S/ 5,500 + Beneficios de ley",
        "ubicacion": "Cerro de Pasco, Pasco (U.M. El Porvenir)",
        "descripcion": (
            "Nexa Resources Perú, importante compañía minera y metalúrgica, requiere incorporar "
            "un Analista de Sistemas y Soporte TI para su operación en Cerro de Pasco. Brindará "
            "soporte a la continuidad tecnológica de los procesos operativos, planta de beneficio y oficinas."
        ),
        "requisitos": (
            "• Egresado o Titulado en Ingeniería de Sistemas y Computación (UNDAC altamente valorado).\n"
            "• Experiencia mínima de 1 año en soporte a infraestructura TI o redes.\n"
            "• Conocimientos sólidos en administración de servidores Windows/Linux y bases de datos MySQL/SQL Server.\n"
            "• Disponibilidad para laborar bajo régimen atípico en campamento minero en Pasco."
        ),
        "funciones": (
            "1. Garantizar la disponibilidad operativa de redes LAN/WAN y enlaces de fibra óptica en planta.\n"
            "2. Administrar el parque informático, cuentas de usuario y políticas de seguridad.\n"
            "3. Ejecutar respaldos de información y soporte preventivo a terminales industriales.\n"
            "4. Coordinar con proveedores de telecomunicaciones e implementar mejoras continuas."
        ),
        "url_original": None,  # Postulación interna en NEXO UNDAC
        "dias_vigencia": 60,
    },
    {
        "empresa_ruc": "20600171221",  # Globant
        "titulo": "Junior Backend Developer (Python / Flask / APIs)",
        "modalidad": "Remoto",
        "tipo_oferta": "Tiempo completo",
        "jornada": "Lunes a Viernes (Horario flexible)",
        "remuneracion": "S/ 3,800 - S/ 5,000 + Seguro privado EPS",
        "ubicacion": "Lima / Remoto (Todo el Perú)",
        "descripcion": (
            "En Globant Perú nos encontramos en búsqueda de un Junior Backend Developer para sumarse a "
            "nuestro equipo de ingeniería de software. Trabajarás desarrollando APIs robustas, integrando "
            "microservicios y participando en proyectos de transformación digital de alto impacto internacional."
        ),
        "requisitos": (
            "• Egresado o Bachiller en Ingeniería de Sistemas, Computación o carreras afines.\n"
            "• Experiencia práctica con Python (Flask, FastAPI o Django).\n"
            "• Manejo de bases de datos relacionales (MySQL, PostgreSQL) y lenguaje SQL.\n"
            "• Conocimiento de control de versiones con Git/GitHub y conceptos de metodologías ágiles (Scrum)."
        ),
        "funciones": (
            "1. Diseñar e implementar APIs RESTful documentadas y escalables.\n"
            "2. Optimizar consultas SQL y estructurar esquemas de base de datos relacionales.\n"
            "3. Participar en revisiones de código (Code Reviews) y pruebas unitarias automatizadas.\n"
            "4. Colaborar con desarrolladores Frontend y diseñadores UX/UI en sprints semanales."
        ),
        "url_original": "https://www.linkedin.com/jobs/view/junior-backend-developer-python-peru",
        "dias_vigencia": 90,
    },
    {
        "empresa_ruc": "20100047218",  # BCP
        "titulo": "Practicante Profesional de Business Intelligence y Datos (Power BI / SQL)",
        "modalidad": "Híbrido",
        "tipo_oferta": "Prácticas profesionales",
        "jornada": "40 horas semanales (Lunes a Viernes)",
        "remuneracion": "S/ 1,800 - S/ 2,200 (Convenio de Prácticas + Seguro FOLA)",
        "ubicacion": "Lima / Híbrido (2 días oficina, 3 remoto)",
        "descripcion": (
            "El Banco de Crédito del Perú (BCP) busca talento joven con pasión por los datos. Formarás "
            "parte de la División de Analítica e Inteligencia de Negocios, aprendiendo a modelar datos, "
            "automatizar dashboards y transformar información en decisiones financieras estratégicas."
        ),
        "requisitos": (
            "• Egresado universitario (2024 o 2025) de Ingeniería de Sistemas, Computación o Estadística.\n"
            "• Manejo intermedio de SQL (consultas complejas, agrupaciones, subconsultas).\n"
            "• Experiencia académica o proyectos con Power BI (DAX y Power Query).\n"
            "• Deseable conocimiento básico de Python para análisis de datos (Pandas)."
        ),
        "funciones": (
            "1. Construir y mantener tableros de control ejecutivos en Microsoft Power BI.\n"
            "2. Extraer, transformar y limpiar datos procedentes de los almacenes corporativos.\n"
            "3. Automatizar la generación de reportes operativos semanales y mensuales.\n"
            "4. Proponer indicadores clave (KPI) para el seguimiento de productos digitales del banco."
        ),
        "url_original": "https://jobs.bcp.com.pe/oportunidad-practicante-bi-datos-lima",
        "dias_vigencia": 45,
    },
    {
        "empresa_ruc": "20419471018",  # Volcan
        "titulo": "Administrador de Redes y Ciberseguridad Jr.",
        "modalidad": "Presencial",
        "tipo_oferta": "Tiempo completo",
        "jornada": "Lunes a Sábado",
        "remuneracion": "S/ 3,500 - S/ 4,200 + Alimentación cubierta",
        "ubicacion": "Cerro de Pasco, Pasco",
        "descripcion": (
            "Volcan Compañía Minera requiere un Administrador de Redes y Seguridad Informática Jr. para "
            "su sede en Cerro de Pasco. Se encargará de resguardar la infraestructura de red, asegurar el "
            "cumplimiento de políticas de seguridad y atender incidentes tecnológicos en planta y oficinas."
        ),
        "requisitos": (
            "• Egresado o Bachiller en Ingeniería de Sistemas y Computación de la UNDAC.\n"
            "• Conocimientos en switching, routing (Cisco/MikroTik) y firewalls (Fortinet).\n"
            "• Nociones de buenas prácticas de ciberseguridad, respaldo de datos y recuperación ante desastres.\n"
            "• Radicar en Pasco o con disponibilidad inmediata de residencia local."
        ),
        "funciones": (
            "1. Monitorear el tráfico de red y el estado de la seguridad perimetral de la empresa.\n"
            "2. Configurar switches, routers y puntos de acceso inalámbrico en oficinas y campamento.\n"
            "3. Gestionar políticas de contraseñas, accesos VPN y copias de seguridad de servidores.\n"
            "4. Brindar atención de primer y segundo nivel ante eventos de seguridad o caídas de red."
        ),
        "url_original": None,  # Postulación interna NEXO
        "dias_vigencia": 60,
    },
    {
        "empresa_ruc": "20380312675",  # NTT DATA
        "titulo": "Cloud & DevOps Engineer Trainee (AWS / Linux / Docker)",
        "modalidad": "Remoto",
        "tipo_oferta": "Tiempo completo",
        "jornada": "Lunes a Viernes",
        "remuneracion": "S/ 3,200 - S/ 4,000 + Capacitación y certificaciones oficiales pagadas",
        "ubicacion": "Remoto (A nivel nacional)",
        "descripcion": (
            "NTT DATA Perú, líder mundial en servicios de consultoría y tecnología, abre su programa Trainee "
            "Cloud & DevOps para egresados universitarios. Recibirás formación de clase mundial en computación en la nube "
            "y participarás en el despliegue de infraestructuras modernas."
        ),
        "requisitos": (
            "• Egresado de Ingeniería de Sistemas y Computación.\n"
            "• Dominio básico de entornos Linux (línea de comandos, scripting en Bash o Python).\n"
            "• Conceptos claros de contenedores (Docker) y fundamentos de Cloud (AWS, Azure o GCP).\n"
            "• Actitud proactiva, ganas de aprender y capacidad para trabajar en equipo remoto."
        ),
        "funciones": (
            "1. Apoyar en la configuración y mantenimiento de pipelines de CI/CD (GitHub Actions / GitLab).\n"
            "2. Desplegar servicios y contenedores en infraestructuras cloud bajo supervisión de un Senior.\n"
            "3. Monitorear alertas de rendimiento y logs de aplicaciones en la nube.\n"
            "4. Completar las rutas de certificación Cloud subvencionadas por la empresa."
        ),
        "url_original": "https://careers.nttdata.com/job/peru-cloud-trainee-remote",
        "dias_vigencia": 75,
    },
    {
        "empresa_ruc": "20100017491",  # Telefónica
        "titulo": "Desarrollador Web Frontend (JavaScript / UI-UX)",
        "modalidad": "Híbrido",
        "tipo_oferta": "Tiempo completo",
        "jornada": "Lunes a Viernes",
        "remuneracion": "S/ 3,600 - S/ 4,500 + Beneficios corporativos",
        "ubicacion": "Lima / Híbrido",
        "descripcion": (
            "Telefónica del Perú busca incorporar a su equipo digital un Desarrollador Web Frontend. "
            "Serás responsable de construir experiencias de usuario intuitivas y dinámicas para nuestros "
            "portales y aplicaciones web corporativas."
        ),
        "requisitos": (
            "• Egresado o Bachiller de Ingeniería de Sistemas o afines.\n"
            "• Dominio de HTML5 semántico, CSS3 moderno, Bootstrap / Tailwind y JavaScript ES6+.\n"
            "• Experiencia en consumo de APIs REST mediante Fetch o Axios.\n"
            "• Cuidado por el diseño responsive, rendimiento web y accesibilidad."
        ),
        "funciones": (
            "1. Maquetar e implementar vistas web funcionales a partir de prototipos en Figma.\n"
            "2. Conectar interfaces de usuario con microservicios y APIs backend.\n"
            "3. Diagnosticar y resolver errores de compatibilidad entre navegadores y dispositivos móviles.\n"
            "4. Optimizar el tiempo de carga y la interactividad de las aplicaciones web."
        ),
        "url_original": None,  # Postulación interna NEXO
        "dias_vigencia": 50,
    }
]


def main():
    app = create_app()
    with app.app_context():
        print("=" * 65)
        print(" POBLANDO PLATAFORMA CON EMPRESAS Y OFERTAS LABORALES REALES")
        print("=" * 65)

        # 1. Crear Sectores
        sectores_map = {}
        for nombre in SECTORES_REALES:
            s = Sectores.query.filter_by(nombre=nombre).first()
            if not s:
                s = Sectores(nombre=nombre)
                db.session.add(s)
                db.session.flush()
                print(f"✔ Sector creado: {nombre}")
            sectores_map[nombre] = s.id_sector
        db.session.commit()

        # 2. Crear Empresas reales
        empresas_map = {}
        for edata in EMPRESAS_REALES:
            emp = Empresas.query.filter_by(ruc=edata["ruc"]).first()
            id_sec = sectores_map.get(edata["sector"])
            if not emp:
                emp = Empresas(
                    ruc=edata["ruc"],
                    razon_social=edata["razon_social"],
                    nombre_comercial=edata["nombre_comercial"],
                    id_sector=id_sec,
                    tipo_empresa=edata["tipo_empresa"],
                    direccion=edata["direccion"],
                    distrito=edata["distrito"],
                    provincia=edata["provincia"],
                    region=edata["region"],
                    pais="Perú",
                    telefono=edata["telefono"],
                    sitio_web=edata["sitio_web"],
                    estado="activa"
                )
                db.session.add(emp)
                db.session.flush()
                print(f"✔ Empresa registrada: {emp.nombre_comercial} (RUC {emp.ruc})")
            empresas_map[edata["ruc"]] = emp
        db.session.commit()

        # 3. Crear Ofertas Laborales reales
        ofertas_creadas = {}
        hoy = date.today()
        for odata in OFERTAS_REALES:
            emp = empresas_map[odata["empresa_ruc"]]
            of = OfertasLaborales.query.filter_by(titulo=odata["titulo"], id_empresa=emp.id_empresa).first()
            fecha_venc = hoy + timedelta(days=odata["dias_vigencia"])
            if not of:
                of = OfertasLaborales(
                    id_creado_por=1,  # Administrador
                    id_empresa=emp.id_empresa,
                    titulo=odata["titulo"],
                    empresa=emp.nombre_comercial,
                    telefono=emp.telefono,
                    descripcion=odata["descripcion"],
                    requisitos=odata["requisitos"],
                    modalidad=odata["modalidad"],
                    tipo_oferta=odata["tipo_oferta"],
                    jornada=odata["jornada"],
                    remuneracion=odata["remuneracion"],
                    funciones=odata["funciones"],
                    ubicacion=odata["ubicacion"],
                    url_original=odata["url_original"],
                    fuente="manual",
                    fecha_publicacion=hoy - timedelta(days=5),
                    fecha_vencimiento=fecha_venc,
                    activa=1
                )
                db.session.add(of)
                db.session.flush()
                print(f"✔ Oferta creada: '{of.titulo}' - {emp.nombre_comercial}")
            ofertas_creadas[odata["titulo"]] = of
        db.session.commit()

        # 4. Simular actividad para el egresado Carlos Quispe (DNI 70000001)
        carlos = Egresados.query.filter_by(dni="70000001").first()
        if carlos:
            print("\n--- Vinculando actividad realista para Carlos Quispe ---")
            
            # A) Guardar 2 ofertas de interés
            titulos_guardar = [
                "Junior Backend Developer (Python / Flask / APIs)",
                "Practicante Profesional de Business Intelligence y Datos (Power BI / SQL)"
            ]
            for tg in titulos_guardar:
                of_g = ofertas_creadas.get(tg)
                if of_g:
                    existe = OfertasGuardadas.query.filter_by(id_egresado=carlos.id_egresado, id_oferta=of_g.id_oferta).first()
                    if not existe:
                        db.session.add(OfertasGuardadas(
                            id_egresado=carlos.id_egresado,
                            id_oferta=of_g.id_oferta,
                            fecha=datetime.utcnow() - timedelta(days=3)
                        ))
                        print(f"✔ Oferta guardada en favoritos: {of_g.titulo}")

            # B) Postulación interna enviada a Nexa Resources (Operación Cerro de Pasco)
            of_nexa = ofertas_creadas.get("Analista de Sistemas y Soporte TI en Unidad Minera")
            if of_nexa:
                post = Postulaciones.query.filter_by(id_egresado=carlos.id_egresado, id_oferta=of_nexa.id_oferta).first()
                if not post:
                    db.session.add(Postulaciones(
                        id_egresado=carlos.id_egresado,
                        id_oferta=of_nexa.id_oferta,
                        mensaje=(
                            "Estimados responsables de selección de Nexa Resources Perú: Como egresado de Ingeniería "
                            "de Sistemas y Computación de la UNDAC, presento mi postulación para la vacante de Analista "
                            "de Sistemas en Pasco. Cuento con formación en redes, bases de datos y soporte operativo, "
                            "con plena disposición para desempeñarme bajo régimen de campamento en El Porvenir."
                        ),
                        estado="en_revision",
                        fecha=datetime.utcnow() - timedelta(days=4)
                    ))
                    print(f"✔ Postulación interna registrada: {of_nexa.titulo} [Estado: En revisión]")

            # C) Seguimiento externo para Globant (Estado: Entrevista)
            of_globant = ofertas_creadas.get("Junior Backend Developer (Python / Flask / APIs)")
            if of_globant:
                seg1 = SeguimientoExterno.query.filter_by(id_egresado=carlos.id_egresado, id_oferta=of_globant.id_oferta).first()
                if not seg1:
                    db.session.add(SeguimientoExterno(
                        id_egresado=carlos.id_egresado,
                        id_oferta=of_globant.id_oferta,
                        estado="entrevista",
                        visitas=4,
                        observacion="Envié mi CV por LinkedIn. Recibí correo de selección de Globant citándome a la primera entrevista técnica.",
                        fecha_postulacion=hoy - timedelta(days=6),
                        fecha_contratacion=None
                    ))
                    print(f"✔ Seguimiento externo registrado: {of_globant.titulo} [Estado: Entrevista (4 visitas)]")

            # D) Seguimiento externo para NTT DATA (Estado: Postulado)
            of_ntt = ofertas_creadas.get("Cloud & DevOps Engineer Trainee (AWS / Linux / Docker)")
            if of_ntt:
                seg2 = SeguimientoExterno.query.filter_by(id_egresado=carlos.id_egresado, id_oferta=of_ntt.id_oferta).first()
                if not seg2:
                    db.session.add(SeguimientoExterno(
                        id_egresado=carlos.id_egresado,
                        id_oferta=of_ntt.id_oferta,
                        estado="postulado",
                        visitas=2,
                        observacion="Postulé a través del portal de carreras NTT DATA Trainee. Pendiente de revisión inicial de filtros.",
                        fecha_postulacion=hoy - timedelta(days=2),
                        fecha_contratacion=None
                    ))
                    print(f"✔ Seguimiento externo registrado: {of_ntt.titulo} [Estado: Postulado (2 visitas)]")

            db.session.commit()

        print("\n" + "=" * 65)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 65)


if __name__ == "__main__":
    main()
