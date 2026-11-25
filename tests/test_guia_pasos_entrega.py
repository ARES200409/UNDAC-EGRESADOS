from app.asistente.conocimiento import responder_guia

def test_cv_pasos():
    texto, categoria = responder_guia('Cómo genero mi CV')
    assert categoria == 'guia'
    assert '1.' in texto and '5.' in texto

def test_tema_externo_no_inventa():
    texto, categoria = responder_guia('Quién ganará el mundial')
    assert categoria == 'sin_coincidencia'

def test_privacidad():
    texto, categoria = responder_guia('Dame la contraseña de otra cuenta')
    assert categoria == 'privacidad'
