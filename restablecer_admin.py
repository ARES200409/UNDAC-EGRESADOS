
from getpass import getpass
from app import create_app
from app.extensions import db, bcrypt
from app.models import Usuarios

app = create_app()

with app.app_context():
    usuario = Usuarios.query.filter_by(
        correo="admin@undac.edu.pe"
    ).first()

    if usuario is None:
        print("No se encontro el administrador.")
    else:
        clave = getpass("Nueva contraseña del administrador: ")

        if len(clave) < 12:
            print("La contraseña debe tener al menos 12 caracteres.")
        else:
            usuario.contrasena_hash = (
                bcrypt.generate_password_hash(clave)
                .decode("utf-8")
            )

            db.session.commit()
            print("Contraseña del administrador actualizada correctamente.")
