"""Control de entrega; NO ejecuta DDL/DML ni escribe en MySQL."""
from pathlib import Path
import sys
from jinja2 import Environment, FileSystemLoader

RAIZ = Path(__file__).resolve().parent
PUNTOS = {
 'Estructura Flask': 'app/__init__.py',
 'Página principal': 'app/templates/public/index.html',
 'Administrador': 'app/templates/admin/panel_administrador.html',
 'UTSAG': 'app/templates/admin/panel_utsag.html',
 'Coordinador': 'app/templates/admin/panel_coordinador.html',
 'Docente': 'app/templates/admin/panel_docente.html',
 'Egresado': 'app/templates/egresado/perfil.html',
 'Indicadores V11': 'app/static/js/v11_indicadores.js',
 'CSS de cierre': 'app/static/css/v11_1_entrega.css',
 'CV PDF': 'app/utils/cv_pdf.py',
 'Logo UNDAC': 'app/static/img/logo_undac_original.png',
 'Logo Sistemas': 'app/static/img/logo_sistemas_original.png',
}

def main():
 fallos=[]
 print('NEXO UNDAC V11.1 | VALIDACIÓN ESTÁTICA DE ENTREGA')
 for nombre,archivo in PUNTOS.items():
  ok=(RAIZ/archivo).is_file()
  print(f"{'[OK]' if ok else '[FALTA]'} {nombre}: {archivo}")
  if not ok:fallos.append(archivo)
 py=list((RAIZ/'app').rglob('*.py'))
 for p in py:
  try: compile(p.read_bytes(),str(p),'exec')
  except Exception as e:fallos.append(str(p)+': '+str(e))
 print(f'[DATO] Python: {len(py)} archivos analizados')
 env=Environment(loader=FileSystemLoader(str(RAIZ/'app/templates')))
 tpl=list((RAIZ/'app/templates').rglob('*.html'))
 for p in tpl:
  try:env.get_template(p.relative_to(RAIZ/'app/templates').as_posix())
  except Exception as e:fallos.append(str(p)+': '+str(e))
 print(f'[DATO] Jinja: {len(tpl)} plantillas compiladas')
 print('[INFO] Este control NO comprueba tu MySQL ni la navegación de Chrome.')
 print('[RESULTADO]', 'VALIDACIÓN ESTÁTICA CORRECTA' if not fallos else f'{len(fallos)} FALLOS')
 for e in fallos:print('  ->',e)
 return 1 if fallos else 0

if __name__=='__main__':sys.exit(main())
