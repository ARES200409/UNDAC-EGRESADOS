
# ============================================================
# SISTEMA WEB DE SEGUIMIENTO DE EGRESADOS - UNDAC
# Archivo: run.py
# Descripcion: Punto de entrada de la aplicacion Flask
# ============================================================

from app import create_app

# Crear la aplicacion Flask
app = create_app()


if __name__ == "__main__":
    print("=" * 60)
    print(" SISTEMA DE SEGUIMIENTO DE EGRESADOS - UNDAC")
    print("=" * 60)
    print(" Servidor: Flask")
    print(" Base de datos: MySQL")
    print(" Direccion: http://127.0.0.1:5000")
    print(" Modo depuracion: Desactivado")
    print("=" * 60)

    # Iniciar servidor de desarrollo local
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
