from app.forms.base import IddunForm
from wtforms import BooleanField, PasswordField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegisterForm(IddunForm):
    # QA-001 B2: escolha de jornada, nunca um segundo usuário ou papel.
    # Default client mantém os cadastros legados sem o campo compatíveis.
    account_type = RadioField(
        "Quero usar o IDDUN como",
        choices=[("client", "Cliente"), ("professional", "Profissional")],
        default="client",
        validators=[DataRequired()],
    )
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


class LoginForm(IddunForm):
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



class PasswordResetRequestForm(IddunForm):
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


class PasswordResetForm(IddunForm):
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



class DeleteAccountForm(IddunForm):
    password = PasswordField(
        "Senha atual",
        validators=[
            DataRequired(),
            Length(max=128),
        ],
    )
    confirm = BooleanField(
        (
            "Entendo que minha conta será "
            "desativada e meus dados pessoais "
            "serão anonimizados."
        ),
        validators=[
            DataRequired(
                message=(
                    "Confirme que você entende "
                    "as consequências da exclusão."
                )
            )
        ],
    )
    submit = SubmitField(
        "Excluir minha conta"
    )
