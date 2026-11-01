from app.forms.base import IddunForm
from flask_wtf.file import FileAllowed, FileField, FileSize, MultipleFileField
from wtforms import BooleanField, DateField, DecimalField, IntegerField, RadioField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, Regexp, URL
from wtforms.widgets import CheckboxInput, HiddenInput, ListWidget

from app.models.professional import ProfileTheme
from app.models.experience import ExperienceCategory
from app.services.establishment_readiness_service import DESCRIPTION_MIN_LENGTH
from app.services.onboarding_steps import BIO_MIN_LENGTH, BUSINESS_CATEGORIES, PROFESSIONAL_CATEGORIES


IMAGE_VALIDATORS = [
    FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG ou WEBP."),
    FileSize(max_size=5 * 1024 * 1024, message="A imagem deve ter no máximo 5 MB."),
]


def focus_field(default=50):
    return IntegerField(default=default, validators=[Optional(), NumberRange(min=0, max=100)], widget=HiddenInput())


class WorkModeChoiceForm(IddunForm):
    mode = RadioField(
        "Como você trabalha hoje?",
        choices=[
            ("professional", "Atendo como profissional"),
            ("business", "Tenho ou represento um estabelecimento"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Continuar")


class CheckboxGroupField(SelectMultipleField):
    """V-02b (BUG-001): escolha múltipla como caixas de seleção.

    Mesmos dados e validação do SelectMultipleField; só muda o widget, então
    o valor enviado (uma lista com o mesmo nome) continua igual.
    """

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


ATTENDANCE_MODALITY_CHOICES = [
    ("establishment", "Em estabelecimento"),
    ("own_space", "Em espaço próprio"),
    ("client_location", "No endereço do cliente"),
]

PROFESSIONAL_AREA_CHOICES = list(PROFESSIONAL_CATEGORIES.items())


# Onboarding Profissional por etapas (PR 2): um formulário por pergunta.
# As regras de negócio ficam no serviço compartilhado com a API do app;
# estes formulários só validam formato e obrigatoriedade da etapa.


class ProStepIdentityForm(IddunForm):
    display_name = StringField(
        "Nome profissional",
        validators=[DataRequired(message="Informe seu nome profissional."), Length(min=2, max=140)],
    )
    submit = SubmitField("Continuar")


class ProStepLocationForm(IddunForm):
    city = StringField(
        "Cidade",
        validators=[DataRequired(message="Informe a cidade onde você atende."), Length(min=2, max=100)],
    )
    state = StringField(
        "UF",
        validators=[
            DataRequired(message="Informe a UF onde você atende."),
            Length(min=2, max=2, message="Use as duas letras da UF."),
            Regexp(r"^[A-Za-z]{2}$", message="Use as duas letras da UF."),
        ],
    )
    submit = SubmitField("Continuar")


class ProStepSpecialtyForm(IddunForm):
    primary_specialty = StringField(
        "Especialidade principal",
        validators=[DataRequired(message="Informe sua especialidade principal."), Length(min=2, max=120)],
    )
    categories = CheckboxGroupField(
        "Áreas de atuação",
        choices=PROFESSIONAL_AREA_CHOICES,
        validators=[DataRequired(message="Escolha pelo menos uma área de atuação.")],
    )
    submit = SubmitField("Continuar")


class ProStepModalityForm(IddunForm):
    attendance_modalities = CheckboxGroupField(
        "Como você atende?",
        choices=ATTENDANCE_MODALITY_CHOICES,
        validators=[DataRequired(message="Selecione pelo menos uma modalidade de atendimento.")],
    )
    submit = SubmitField("Continuar")


class ProStepPresentationForm(IddunForm):
    headline = StringField("Chamada (opcional)", validators=[Optional(), Length(max=180)])
    bio = TextAreaField(
        "Apresentação",
        validators=[
            DataRequired(message="Escreva sua apresentação."),
            Length(
                min=BIO_MIN_LENGTH,
                max=2000,
                message=f"Use entre {BIO_MIN_LENGTH} e 2000 caracteres.",
            ),
        ],
    )
    submit = SubmitField("Continuar")


class ProStepPersonalizeForm(IddunForm):
    avatar_file = FileField("Foto de perfil", validators=[Optional(), *IMAGE_VALIDATORS])
    cover_file = FileField("Foto de capa", validators=[Optional(), *IMAGE_VALIDATORS])
    avatar_focus_x = focus_field()
    avatar_focus_y = focus_field()
    cover_focus_x = focus_field()
    cover_focus_y = focus_field()
    portfolio_files = MultipleFileField("Trabalhos")
    phone = StringField("WhatsApp / telefone", validators=[Optional(), Length(max=32)])
    whatsapp_enabled = BooleanField("Mostrar botão do WhatsApp no meu perfil", default=True)
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    # D-ONB-03: opcional, padrão Beleza.
    visual_theme = SelectField(
        "Universo visual",
        choices=ProfileTheme.CHOICES,
        validators=[Optional()],
        default=ProfileTheme.BEAUTY,
    )
    submit = SubmitField("Salvar e continuar")


class ProPublishForm(IddunForm):
    submit = SubmitField("Publicar perfil")


class ProfessionalEditForm(IddunForm):
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
    attendance_modalities = CheckboxGroupField(
        "Onde você atende?",
        choices=[
            ("establishment", "Em estabelecimento"),
            ("own_space", "Em espaço próprio"),
            ("client_location", "No endereço do cliente"),
        ],
        validators=[DataRequired(message="Selecione pelo menos uma modalidade de atendimento.")],
    )
    visual_theme = SelectField("Universo visual", choices=ProfileTheme.CHOICES, validators=[DataRequired()])
    portfolio_files = MultipleFileField("Adicionar trabalhos")
    submit = SubmitField("Salvar perfil")



class ProfessionalWorkExperienceForm(IddunForm):
    company_name = StringField(
        "Estabelecimento ou empresa",
        validators=[DataRequired(), Length(max=160)],
    )
    role_title = StringField(
        "Cargo ou função",
        validators=[DataRequired(), Length(max=140)],
    )
    started_at = DateField(
        "Data de início", validators=[DataRequired()],
    )
    ended_at = DateField(
        "Data de término", validators=[Optional()],
    )
    is_current = BooleanField("Trabalho aqui atualmente")
    description = TextAreaField(
        "Descrição", validators=[Optional(), Length(max=2000)],
    )
    submit = SubmitField("Adicionar experiência")



class ProfessionalServiceDraftForm(IddunForm):
    establishment_id = SelectField("Local do atendimento", coerce=int, choices=[(0, "Sem estabelecimento vinculado")], validators=[Optional()])
    image_file = FileField("Imagem de capa do serviço", validators=[Optional(), *IMAGE_VALIDATORS])
    title = StringField(
        "Nome do serviço", validators=[DataRequired(), Length(max=160)],
    )
    category = SelectField(
        "Categoria", choices=ExperienceCategory.CHOICES,
        validators=[DataRequired()],
    )
    short_description = StringField(
        "Descrição resumida", validators=[DataRequired(), Length(max=220)],
    )
    description = TextAreaField(
        "Descrição completa", validators=[Optional(), Length(max=4000)],
    )
    regular_price = DecimalField(
        "Preço regular (R$)", places=2,
        validators=[DataRequired(), NumberRange(min=0)],
    )
    price = DecimalField(
        "Preço IDDUN (R$)", places=2,
        validators=[DataRequired(), NumberRange(min=0)],
    )
    duration_minutes = IntegerField(
        "Duração em minutos",
        validators=[DataRequired(), NumberRange(min=10, max=720)],
        default=60,
    )
    submit = SubmitField("Salvar rascunho")

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)
        if (
            self.regular_price.data is not None
            and self.price.data is not None
            and self.price.data > self.regular_price.data
        ):
            self.price.errors.append(
                "O preço IDDUN não pode ser maior que o preço regular."
            )
            valid = False
        return valid


BUSINESS_CATEGORY_CHOICES = list(BUSINESS_CATEGORIES.items())


OPERATION_MODE_CHOICES = [
    ("physical", "No estabelecimento"),
    ("mobile", "No endereço do cliente"),
    ("hybrid", "Nos dois (híbrido)"),
]

HOURS_MODE_CHOICES = [
    ("scheduled", "Sob agendamento"),
    ("fixed_hours", "Horários fixos"),
]

WEEKDAY_FIELDS = (
    ("monday", "segunda"), ("tuesday", "terça"), ("wednesday", "quarta"),
    ("thursday", "quinta"), ("friday", "sexta"), ("saturday", "sábado"),
    ("sunday", "domingo"),
)


class RadioCardField(RadioField):
    """Escolha única como cartões: a mesma lista, com input nativo."""


# Cadastro de Estabelecimento por etapas (PR 3). Regras de negócio no
# serviço compartilhado com a API do app; aqui só formato e obrigatório.


class BizStepBasicsForm(IddunForm):
    name = StringField(
        "Nome do estabelecimento",
        validators=[DataRequired(message="Informe o nome do estabelecimento."), Length(min=2, max=160)],
    )
    category = RadioCardField(
        "Tipo de estabelecimento",
        choices=BUSINESS_CATEGORY_CHOICES,
        validators=[DataRequired(message="Escolha o tipo de estabelecimento.")],
    )
    city = StringField(
        "Cidade",
        validators=[DataRequired(message="Informe cidade e UF."), Length(min=2, max=100)],
    )
    state = StringField(
        "UF",
        validators=[
            DataRequired(message="Informe cidade e UF."),
            Length(min=2, max=2, message="Use as duas letras da UF."),
            Regexp(r"^[A-Za-z]{2}$", message="Use as duas letras da UF."),
        ],
    )
    submit = SubmitField("Continuar")


class BizStepOperationForm(IddunForm):
    operation_mode = RadioCardField(
        "Como o estabelecimento atende?",
        choices=OPERATION_MODE_CHOICES,
        validators=[DataRequired(message="Diga como o estabelecimento atende.")],
    )
    submit = SubmitField("Continuar")


class BizStepAddressForm(IddunForm):
    address_line1 = StringField(
        "Endereço comercial",
        validators=[DataRequired(message="Informe o endereço comercial."), Length(max=180)],
    )
    address_line2 = StringField("Complemento (opcional)", validators=[Optional(), Length(max=120)])
    neighborhood = StringField("Bairro (opcional)", validators=[Optional(), Length(max=100)])
    postal_code = StringField(
        "CEP (opcional)",
        # Só tamanho, como a API: o critério de endereço válido ainda não foi
        # aprovado (FLOW-EST-001, pendências de granularidade).
        validators=[Optional(), Length(max=16)],
    )
    submit = SubmitField("Continuar")


class BizStepHoursForm(IddunForm):
    business_hours_mode = RadioCardField(
        "Funcionamento",
        choices=HOURS_MODE_CHOICES,
        validators=[DataRequired(message="Defina o funcionamento: sob agendamento ou horários fixos.")],
    )
    monday_start = StringField("Abertura na segunda", validators=[Optional()])
    monday_end = StringField("Fechamento na segunda", validators=[Optional()])
    tuesday_start = StringField("Abertura na terça", validators=[Optional()])
    tuesday_end = StringField("Fechamento na terça", validators=[Optional()])
    wednesday_start = StringField("Abertura na quarta", validators=[Optional()])
    wednesday_end = StringField("Fechamento na quarta", validators=[Optional()])
    thursday_start = StringField("Abertura na quinta", validators=[Optional()])
    thursday_end = StringField("Fechamento na quinta", validators=[Optional()])
    friday_start = StringField("Abertura na sexta", validators=[Optional()])
    friday_end = StringField("Fechamento na sexta", validators=[Optional()])
    saturday_start = StringField("Abertura no sábado", validators=[Optional()])
    saturday_end = StringField("Fechamento no sábado", validators=[Optional()])
    sunday_start = StringField("Abertura no domingo", validators=[Optional()])
    sunday_end = StringField("Fechamento no domingo", validators=[Optional()])
    submit = SubmitField("Continuar")


class BizStepContactForm(IddunForm):
    description = TextAreaField(
        "Apresentação",
        validators=[
            DataRequired(message="Escreva a apresentação do estabelecimento."),
            Length(
                min=DESCRIPTION_MIN_LENGTH,
                max=2000,
                message=f"Use entre {DESCRIPTION_MIN_LENGTH} e 2000 caracteres.",
            ),
        ],
    )
    phone = StringField("Telefone / WhatsApp", validators=[Optional(), Length(max=32)])
    whatsapp_enabled = BooleanField("Mostrar botão do WhatsApp na página", default=True)
    email = StringField(
        "E-mail comercial",
        validators=[Optional(), Email(message="Informe um e-mail válido."), Length(max=255)],
    )
    instagram = StringField("Instagram (opcional)", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Continuar")

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators)
        if not (self.phone.data or "").strip() and not (self.email.data or "").strip():
            self.phone.errors.append("Informe telefone ou e-mail comercial.")
            return False
        return valid


class BizStepMediaForm(IddunForm):
    logo_file = FileField("Logo", validators=[Optional(), *IMAGE_VALIDATORS])
    cover_file = FileField("Foto de capa", validators=[Optional(), *IMAGE_VALIDATORS])
    logo_focus_x = focus_field()
    logo_focus_y = focus_field()
    cover_focus_x = focus_field()
    cover_focus_y = focus_field()
    gallery_files = MultipleFileField("Fotos do espaço")
    submit = SubmitField("Salvar e continuar")


class BizPublishForm(IddunForm):
    submit = SubmitField("Publicar página")


class BusinessOnboardingForm(IddunForm):
    # DEC-ID-101 / D-QA-01: logo, capa e fotos são opcionais para publicar.
    logo_file = FileField("Logo", validators=[Optional(), *IMAGE_VALIDATORS])
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
    operation_mode = SelectField("Modalidade de atendimento", choices=[("", "Definir depois"), ("physical", "No estabelecimento"), ("mobile", "No endereço do cliente"), ("hybrid", "Híbrido")], validators=[Optional()])
    business_hours_mode = SelectField("Funcionamento", choices=[("", "Definir depois"), ("scheduled", "Sob agendamento"), ("fixed_hours", "Horários fixos")], validators=[Optional()])
    monday_start = StringField("Abertura na segunda", validators=[Optional()])
    monday_end = StringField("Fechamento na segunda", validators=[Optional()])
    tuesday_start = StringField("Abertura na terça", validators=[Optional()])
    tuesday_end = StringField("Fechamento na terça", validators=[Optional()])
    wednesday_start = StringField("Abertura na quarta", validators=[Optional()])
    wednesday_end = StringField("Fechamento na quarta", validators=[Optional()])
    thursday_start = StringField("Abertura na quinta", validators=[Optional()])
    thursday_end = StringField("Fechamento na quinta", validators=[Optional()])
    friday_start = StringField("Abertura na sexta", validators=[Optional()])
    friday_end = StringField("Fechamento na sexta", validators=[Optional()])
    saturday_start = StringField("Abertura no sábado", validators=[Optional()])
    saturday_end = StringField("Fechamento no sábado", validators=[Optional()])
    sunday_start = StringField("Abertura no domingo", validators=[Optional()])
    sunday_end = StringField("Fechamento no domingo", validators=[Optional()])
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


class TeamMemberForm(IddunForm):
    email = StringField("E-mail da conta IDDUN do profissional", validators=[DataRequired(), Email(), Length(max=255)])
    role_name = StringField("Função no estabelecimento", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Enviar convite")


CERTIFICATE_FILE_VALIDATORS = [
    FileAllowed(["pdf", "jpg", "jpeg", "png", "webp"], "Use PDF, JPG, PNG ou WEBP."),
    FileSize(max_size=8 * 1024 * 1024, message="O certificado deve ter no máximo 8 MB."),
]


class ProfessionalCertificationForm(IddunForm):
    title = StringField("Certificação", validators=[DataRequired(), Length(min=2, max=180)])
    issuer = StringField("Instituição emissora", validators=[DataRequired(), Length(min=2, max=180)])
    issued_at = DateField("Data de emissão", validators=[Optional()])
    expires_at = DateField("Validade", validators=[Optional()])
    credential_id = StringField("Código / credencial", validators=[Optional(), Length(max=180)])
    verification_url = StringField("URL de verificação", validators=[Optional(), URL(), Length(max=500)])
    document_file = FileField("Comprovante", validators=[Optional(), *CERTIFICATE_FILE_VALIDATORS])
    is_public = BooleanField("Exibir no meu perfil público", default=True)
    submit = SubmitField("Adicionar certificação")
