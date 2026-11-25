# app/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

class LoginForm(FlaskForm):
    correo     = StringField('Correo', validators=[DataRequired(), Email()])
    contrasena = PasswordField('Contraseña', validators=[DataRequired()])
    rol        = SelectField('Ingresar como', validators=[DataRequired()])
    submit     = SubmitField('Ingresar')

class VerificarForm(FlaskForm):
    codigo_universitario = StringField('Código universitario', validators=[DataRequired(), Length(min=10, max=10, message='El código debe tener exactamente 10 dígitos')])
    dni                  = StringField('DNI', validators=[DataRequired(), Length(min=8, max=15)])
    submit               = SubmitField('Verificar')

class CompletarRegistroForm(FlaskForm):
    correo     = StringField('Correo', validators=[DataRequired(), Email()])
    contrasena = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8, message='Mínimo 8 caracteres')])
    confirmar  = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('contrasena', message='Las contraseñas no coinciden')])
    submit     = SubmitField('Crear cuenta')

class CambiarContrasenaForm(FlaskForm):
    contrasena_actual = PasswordField('Contraseña actual', validators=[DataRequired()])
    nueva             = PasswordField('Nueva contraseña', validators=[DataRequired(), Length(min=8)])
    confirmar         = PasswordField('Confirmar nueva contraseña', validators=[DataRequired(), EqualTo('nueva', message='Las contraseñas no coinciden')])
    submit            = SubmitField('Actualizar contraseña')


class RegistroEmpresaForm(FlaskForm):
    ruc              = StringField('RUC', validators=[DataRequired(), Length(min=11, max=11, message='El RUC debe tener 11 dígitos')])
    razon_social     = StringField('Razón social', validators=[DataRequired(), Length(min=3, max=200)])
    nombre_comercial = StringField('Nombre comercial', validators=[Optional(), Length(max=200)])
    id_sector        = SelectField('Sector económico', validators=[DataRequired()], coerce=int)
    direccion        = StringField('Dirección', validators=[Optional(), Length(max=255)])
    telefono         = StringField('Teléfono de contacto', validators=[Optional(), Length(max=20)])
    sitio_web        = StringField('Sitio web (https://...)', validators=[Optional(), Length(max=255)])
    correo           = StringField('Correo corporativo de acceso', validators=[DataRequired(), Email(), Length(max=150)])
    contrasena       = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8, message='Mínimo 8 caracteres')])
    confirmar        = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('contrasena', message='Las contraseñas no coinciden')])
    submit           = SubmitField('Solicitar registro empresarial')