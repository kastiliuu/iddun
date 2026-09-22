from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize, MultipleFileField
from wtforms import BooleanField, DateField, IntegerField, RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, URL
from wtforms.widgets import HiddenInput

from app.models.professional import ProfileTheme


IMAGE_VALIDATORS = [
    FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG ou WEBP."),
    FileSize(max_size=5 * 1024 * 1024, message="A imagem deve ter no máximo 5 MB."),
]


def focus_field(default=50):
    return IntegerField(default=default, validators=[Optional(), NumberRange(min=0, max=100)], widget=HiddenInput())


class WorkModeChoiceForm(FlaskForm):
    mode = RadioField(
        "Como você trabalha hoje?",
        choices=[
            ("professional", "Atendo como profissional"),
            ("business", "Tenho ou represento um estabelecimento"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Continuar")


class ProfessionalOnboardingForm(FlaskForm):
    avatar_file = FileField("Foto de perfil", validators=[FileRequired(), *IMAGE_VALIDATORS])
    cover_file = FileField("Foto de capa", validators=[Optional(), *IMAGE_VALIDATORS])
    avatar_focus_x = focus_field()
    avatar_focus_y = focus_field()
    cover_focus_x = focus_field()
    cover_focus_y = focus_field()
    display_name = StringField("Nome profissional", validators=[DataRequired(), Length(min=2, max=140)])
    headline = StringField("Como você se apresenta?", validators=[Optional(), Length(max=180)])
    primary_specialty = StringField("Especialidade principal", validators=[DataRequired(), Length(max=120)])
    specialties_text = StringField(
        "Outras especialidades",
        validators=[Optional(), Length(max=500)],
        description="Separe por vírgulas.",
    )
    bio = TextAreaField("Sobre você", validators=[DataRequired(), Length(min=40, max=2000)])
    phone = StringField("WhatsApp / telefone", validators=[Optional(), Length(max=32)])
    whatsapp_enabled = BooleanField("Mostrar botão do WhatsApp no meu perfil", default=True)
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    city = StringField("Cidade", validators=[DataRequired(), Length(max=100)])
    state = StringField("UF", validators=[DataRequired(), Length(min=2, max=2)])
    visual_theme = SelectField(
        "Universo visual",
        choices=ProfileTheme.CHOICES,
        validators=[DataRequired()],
        default=ProfileTheme.BEAUTY,
    )
    portfolio_files = MultipleFileField("Portfólio")
    submit = SubmitField("Criar meu perfil")


class ProfessionalEditForm(FlaskForm):
    avatar_file = FileField("Foto de perfil", validators=[Optional(), *IMAGE_VALIDATORS])
    cover_file = FileField("Foto de capa", validators=[Optional(), *IMAGE_VALIDATORS])
    avatar_focus_x = focus_field()
    avatar_focus_y = focus_field()
    cover_focus_x = focus_field()
    cover_focus_y = focus_field()
    display_name = StringField("Nome profissional", validators=[DataRequired(), Length(min=2, max=140)])
    headline = StringField("Headline", validators=[Optional(), Length(max=180)])
    primary_specialty = StringField("Especialidade principal", validators=[DataRequired(), Length(max=120)])
    specialties_text = StringField("Outras especialidades", validators=[Optional(), Length(max=500)])
    bio = TextAreaField("Sobre você", validators=[DataRequired(), Length(min=40, max=2000)])
    phone = StringField("WhatsApp / telefone", validators=[Optional(), Length(max=32)])
    whatsapp_enabled = BooleanField("Mostrar botão do WhatsApp no meu perfil")
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    city = StringField("Cidade", validators=[DataRequired(), Length(max=100)])
    state = StringField("UF", validators=[DataRequired(), Length(min=2, max=2)])
    visual_theme = SelectField("Universo visual", choices=ProfileTheme.CHOICES, validators=[DataRequired()])
    portfolio_files = MultipleFileField("Adicionar trabalhos")
    submit = SubmitField("Salvar perfil")


BUSINESS_CATEGORY_CHOICES = [
    ("salao", "Salão de beleza"),
    ("barbearia", "Barbearia"),
    ("tatuagem", "Estúdio de tatuagem"),
    ("unhas", "Studio de unhas"),
    ("estetica", "Estética"),
    ("bem-estar", "Bem-estar / Spa"),
    ("multisservicos", "Multi-serviços"),
]


class BusinessOnboardingForm(FlaskForm):
    logo_file = FileField("Logo", validators=[FileRequired(), *IMAGE_VALIDATORS])
    cover_file = FileField("Foto de capa", validators=[Optional(), *IMAGE_VALIDATORS])
    logo_focus_x = focus_field()
    logo_focus_y = focus_field()
    cover_focus_x = focus_field()
    cover_focus_y = focus_field()
    name = StringField("Nome do estabelecimento", validators=[DataRequired(), Length(min=2, max=160)])
    category = SelectField("Tipo de estabelecimento", choices=BUSINESS_CATEGORY_CHOICES, validators=[DataRequired()])
    description = TextAreaField("Sobre a empresa", validators=[DataRequired(), Length(min=40, max=2000)])
    phone = StringField("WhatsApp / telefone", validators=[Optional(), Length(max=32)])
    whatsapp_enabled = BooleanField("Mostrar botão do WhatsApp na página da empresa", default=True)
    email = StringField("E-mail comercial", validators=[Optional(), Email(), Length(max=255)])
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    address_line1 = StringField("Endereço", validators=[DataRequired(), Length(max=180)])
    address_line2 = StringField("Complemento", validators=[Optional(), Length(max=120)])
    neighborhood = StringField("Bairro", validators=[Optional(), Length(max=100)])
    city = StringField("Cidade", validators=[DataRequired(), Length(max=100)])
    state = StringField("UF", validators=[DataRequired(), Length(min=2, max=2)])
    postal_code = StringField("CEP", validators=[Optional(), Length(max=16)])
    gallery_files = MultipleFileField("Galeria")
    submit = SubmitField("Criar página da empresa")


class BusinessEditForm(BusinessOnboardingForm):
    logo_file = FileField("Logo", validators=[Optional(), *IMAGE_VALIDATORS])
    submit = SubmitField("Salvar empresa")


class TeamMemberForm(FlaskForm):
    email = StringField("E-mail da conta IDDUN do profissional", validators=[DataRequired(), Email(), Length(max=255)])
    role_name = StringField("Função no estabelecimento", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Enviar convite")


CERTIFICATE_FILE_VALIDATORS = [
    FileAllowed(["pdf", "jpg", "jpeg", "png", "webp"], "Use PDF, JPG, PNG ou WEBP."),
    FileSize(max_size=8 * 1024 * 1024, message="O certificado deve ter no máximo 8 MB."),
]


class ProfessionalCertificationForm(FlaskForm):
    title = StringField("Certificação", validators=[DataRequired(), Length(min=2, max=180)])
    issuer = StringField("Instituição emissora", validators=[DataRequired(), Length(min=2, max=180)])
    issued_at = DateField("Data de emissão", validators=[Optional()])
    expires_at = DateField("Validade", validators=[Optional()])
    credential_id = StringField("Código / credencial", validators=[Optional(), Length(max=180)])
    verification_url = StringField("URL de verificação", validators=[Optional(), URL(), Length(max=500)])
    document_file = FileField("Comprovante", validators=[Optional(), *CERTIFICATE_FILE_VALIDATORS])
    is_public = BooleanField("Exibir no meu perfil público", default=True)
    submit = SubmitField("Adicionar certificação")
