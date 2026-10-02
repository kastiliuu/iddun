from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegisterForm(FlaskForm):
    name = StringField(
        "Nome",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    email = StringField(
        "E-mail",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    confirm_password = PasswordField(
        "Confirmar senha",
        validators=[
            DataRequired(),
            EqualTo("password", message="As senhas precisam ser iguais."),
        ],
    )
    submit = SubmitField("Criar minha conta")


class LoginForm(FlaskForm):
    email = StringField(
        "E-mail",
        validators=[DataRequired(), Email()],
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired()],
    )
    remember = BooleanField("Continuar conectado")
    submit = SubmitField("Entrar")



class PasswordResetRequestForm(FlaskForm):
    email = StringField(
        "E-mail",
        validators=[
            DataRequired(),
            Email(),
            Length(max=255),
        ],
    )
    submit = SubmitField(
        "Enviar link de recuperação"
    )


class PasswordResetForm(FlaskForm):
    password = PasswordField(
        "Nova senha",
        validators=[
            DataRequired(),
            Length(
                min=8,
                max=128,
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirmar nova senha",
        validators=[
            DataRequired(),
            EqualTo(
                "password",
                message=(
                    "As senhas precisam ser iguais."
                ),
            ),
        ],
    )
    submit = SubmitField(
        "Redefinir senha"
    )
