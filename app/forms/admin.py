from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

from app.models.establishment import MembershipStatus
from app.models.experience import ExperienceCategory, ExperienceStatus


TIMEZONE_CHOICES = [
    ("America/Sao_Paulo", "Brasil · Brasília (America/Sao_Paulo)"),
]
IMAGE_VALIDATORS = [
    FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG ou WEBP."),
    FileSize(max_size=5 * 1024 * 1024, message="A imagem deve ter no máximo 5 MB."),
]


class EstablishmentForm(FlaskForm):
    name = StringField("Nome do estabelecimento", validators=[DataRequired(), Length(max=160)])
    slug = StringField("Seu endereço no IDDUN", validators=[Optional(), Length(max=190)])
    description = TextAreaField("Descrição", validators=[Optional(), Length(max=2000)])
    phone = StringField("Telefone", validators=[Optional(), Length(max=32)])
    email = StringField("E-mail", validators=[Optional(), Email(), Length(max=255)])
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    address_line1 = StringField("Endereço", validators=[Optional(), Length(max=180)])
    address_line2 = StringField("Complemento", validators=[Optional(), Length(max=120)])
    neighborhood = StringField("Bairro", validators=[Optional(), Length(max=100)])
    city = StringField("Cidade", validators=[Optional(), Length(max=100)])
    state = StringField("UF", validators=[Optional(), Length(min=2, max=2)])
    postal_code = StringField("CEP", validators=[Optional(), Length(max=16)])
    timezone = SelectField("Fuso horário", choices=TIMEZONE_CHOICES, validators=[DataRequired()], default="America/Sao_Paulo")
    logo_file = FileField("Logo / imagem do estabelecimento", validators=[Optional(), *IMAGE_VALIDATORS])
    is_verified = BooleanField("Estabelecimento verificado")
    is_active = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar estabelecimento")


class ProfessionalForm(FlaskForm):
    display_name = StringField("Nome profissional", validators=[DataRequired(), Length(max=140)])
    slug = StringField("Seu endereço no IDDUN", validators=[Optional(), Length(max=180)])
    primary_specialty = StringField("Especialidade principal", validators=[Optional(), Length(max=120)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=2000)])
    phone = StringField("Telefone", validators=[Optional(), Length(max=32)])
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    city = StringField("Cidade", validators=[Optional(), Length(max=100)])
    state = StringField("UF", validators=[Optional(), Length(min=2, max=2)])
    avatar_file = FileField("Imagem / avatar", validators=[Optional(), *IMAGE_VALIDATORS])
    avatar_focus_x = HiddenField(default="50")
    avatar_focus_y = HiddenField(default="50")
    timezone = SelectField("Fuso horário", choices=TIMEZONE_CHOICES, validators=[DataRequired()], default="America/Sao_Paulo")
    default_booking_cutoff_minutes = IntegerField(
        "Antecedência padrão para reserva (minutos)",
        validators=[DataRequired(), NumberRange(min=5, max=10080)],
        default=60,
    )
    is_verified = BooleanField("Profissional verificado")
    is_active = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar profissional")


class MembershipForm(FlaskForm):
    professional_id = SelectField("Profissional", coerce=int, validators=[DataRequired()])
    establishment_id = SelectField("Estabelecimento", coerce=int, validators=[DataRequired()])
    role_name = StringField("Função no local", validators=[Optional(), Length(max=120)])
    status = SelectField(
        "Status",
        choices=[(MembershipStatus.PENDING, "Pendente · aguarda aceite do profissional")],
        validators=[DataRequired()],
        default=MembershipStatus.PENDING,
    )
    is_primary = BooleanField("Local principal")
    started_at = DateField("Início", validators=[Optional()], format="%Y-%m-%d")
    ended_at = DateField("Fim", validators=[Optional()], format="%Y-%m-%d")
    submit = SubmitField("Salvar vínculo")

    def __init__(self, *args, **kwargs):
        item = kwargs.get("obj")
        super().__init__(*args, **kwargs)

        if item is not None:
            self.status.choices = [
                (MembershipStatus.PENDING, "Pendente · aguarda aceite do profissional"),
                (MembershipStatus.REJECTED, "Recusado"),
                (MembershipStatus.INACTIVE, "Inativo"),
            ]
            if item.status == MembershipStatus.ACTIVE:
                self.status.choices.insert(
                    1,
                    (MembershipStatus.ACTIVE, "Ativo · confirmado pelo profissional"),
                )

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)
        if self.started_at.data and self.ended_at.data and self.ended_at.data < self.started_at.data:
            self.ended_at.errors.append("A data de fim não pode ser anterior à data de início.")
            valid = False
        return valid


class ExperienceForm(FlaskForm):
    title = StringField("Nome da experiência", validators=[DataRequired(), Length(max=160)])
    slug = StringField("Identificador da experiência", validators=[Optional(), Length(max=190)])
    professional_id = SelectField("Profissional", coerce=int, validators=[DataRequired()])
    establishment_id = SelectField("Estabelecimento", coerce=int, validators=[Optional()])
    category = SelectField("Categoria", choices=ExperienceCategory.CHOICES, validators=[DataRequired()])
    short_description = StringField("Resumo", validators=[DataRequired(), Length(max=220)])
    description = TextAreaField("Descrição completa", validators=[Optional(), Length(max=4000)])
    badge = StringField("Selo", validators=[Optional(), Length(max=80)])
    image_file = FileField("Imagem da experiência", validators=[Optional(), *IMAGE_VALIDATORS])
    image_focus_x = HiddenField(default="50")
    image_focus_y = HiddenField(default="50")
    regular_price = DecimalField("Preço regular", places=2, validators=[DataRequired(), NumberRange(min=0)])
    price = DecimalField("Preço IDDUN", places=2, validators=[DataRequired(), NumberRange(min=0)])
    duration_minutes = IntegerField(
        "Duração (minutos)", validators=[DataRequired(), NumberRange(min=10, max=720)], default=60
    )
    booking_cutoff_minutes = IntegerField(
        "Antecedência mínima desta experiência (minutos)",
        validators=[Optional(), NumberRange(min=5, max=10080)],
    )
    status = SelectField("Status", choices=ExperienceStatus.CHOICES, validators=[DataRequired()])
    is_featured = BooleanField("Destaque na Home")
    is_first_experience = BooleanField("Oferta de primeira experiência", default=True)
    submit = SubmitField("Salvar experiência")

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)
        if self.regular_price.data is not None and self.price.data is not None:
            if self.price.data > self.regular_price.data:
                self.price.errors.append("O preço IDDUN não pode ser maior que o preço regular.")
                valid = False
        return valid


class OpportunityBatchForm(FlaskForm):
    experience_id = SelectField("Experiência", coerce=int, validators=[DataRequired()])
    slot_date = DateField("Data", validators=[DataRequired()], format="%Y-%m-%d")
    times = TextAreaField(
        "Horários",
        validators=[DataRequired(), Length(max=800)],
        description="Use HH:MM separados por vírgula ou uma linha por horário.",
    )
    booking_cutoff_minutes = IntegerField(
        "Antecedência específica (minutos)",
        validators=[Optional(), NumberRange(min=5, max=10080)],
    )
    submit = SubmitField("Publicar oportunidades")