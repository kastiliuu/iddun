from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import DateField, StringField, SubmitField
from wtforms.validators import Length, Optional


class ClientProfileForm(FlaskForm):
    avatar_file = FileField(
        "Foto de perfil",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG ou WEBP."),
            FileSize(max_size=5 * 1024 * 1024, message="A imagem deve ter no máximo 5 MB."),
        ],
    )
    name = StringField("Nome", validators=[Length(min=2, max=120)])
    phone = StringField("Telefone", validators=[Optional(), Length(max=32)])
    birth_date = DateField("Data de nascimento", validators=[Optional()], format="%Y-%m-%d")
    city = StringField("Cidade", validators=[Optional(), Length(max=100)])
    state = StringField("UF", validators=[Optional(), Length(min=2, max=2)])
    submit = SubmitField("Salvar alterações")
