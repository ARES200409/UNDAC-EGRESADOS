"""Pruebas HTTP de solo lectura: inicie Flask/Waitress antes de ejecutarlo."""
import sys
import urllib.error
import urllib.request

BASE='http://127.0.0.1:5000'
class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def comprobar(ruta, permitidos):
    req=urllib.request.Request(BASE+ruta, headers={'User-Agent':'NEXO-UNDAC-SMOKE-11.2'})
    try:
        with urllib.request.build_opener(SinRedireccion).open(req,timeout=10) as r:
            estado,cabeceras=r.status,r.headers
    except urllib.error.HTTPError as exc:
        estado,cabeceras=exc.code,exc.headers
    except urllib.error.URLError as exc:
        print(f'[FALLO] {ruta}: servidor inaccesible');return False
    valido=estado in permitidos
    if ruta!='/static/css/v11_institucional.css':
        valido=valido and bool(cabeceras.get('X-Request-ID'))
    print(f"[{'OK' if valido else 'FALLO'}] {ruta}: HTTP {estado}")
    return valido

def main():
    print('PRUEBAS HTTP V11.2 · Solo peticiones GET, sin modificar MySQL')
    rutas=(('/',(200,)),('/login',(200,)),('/ofertas-laborales',(200,)),
      ('/health/live',(200,)),('/health/ready',(200,)),
      ('/admin/api/v11/indicadores',(302,401,403)),
      ('/static/css/v11_institucional.css',(200,)))
    return 0 if all([comprobar(r,e) for r,e in rutas]) else 1
if __name__=='__main__': sys.exit(main())
