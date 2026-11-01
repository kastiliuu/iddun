"""Etapas do onboarding Profissional e Business, iguais no Web e no Expo.

Fonte única da ordem das etapas, do que cada uma exige e das mensagens de
pendência. A etapa atual é calculada a partir dos dados salvos; nada aqui
grava no banco (DEC-ID-070 sem migration).

Quatro situações continuam separadas e nunca são derivadas umas das outras:

- ``registrationComplete``: as etapas obrigatórias do assistente têm dados;
- ``profileComplete``: o critério aprovado de 100% do contexto
  (DEC-ID-107 para Business; regra atual do modelo para Profissional);
- ``published``: a página está no ar por ação explícita (``is_active``);
- reservável: decidido por serviço/oferta, executor e horário real
  (DEC-ID-072/108). Não é calculado neste módulo.

Para Business, cadastro concluído e 100% usam hoje os mesmos critérios
aprovados (DEC-ID-100/103/107), mas permanecem campos distintos para que uma
mudança futura de regra não misture os conceitos.
"""

from app.services.establishment_readiness_service import (
    evaluate_establishment_readiness,
)

PROFESSIONAL_MODALITIES = frozenset({"establishment", "own_space", "client_location"})

# D-ONB-01: as mesmas 8 áreas de atuação no Web e no app.
PROFESSIONAL_CATEGORIES = {
    "cabelo": "Cabelo",
    "unhas": "Unhas",
    "barbearia": "Barbearia",
    "estetica": "Estética",
    "maquiagem": "Maquiagem",
    "sobrancelhas": "Sobrancelhas",
    "tatuagem": "Tatuagem",
    "massagem": "Massagem",
}

# D-ONB-02: apresentação com pelo menos 40 caracteres para publicar, no Web
# e no app. Perfis já publicados não são afetados (a regra só vale no ato de
# publicar e nas novas gravações da etapa).
BIO_MIN_LENGTH = 40
PHYSICAL_MODES = frozenset({"physical", "hybrid"})

# Mensagens compartilhadas: Web e Expo exibem exatamente estes textos.
PROFESSIONAL_REQUIREMENT_LABELS = {
    "display_name": "Informe seu nome profissional.",
    "city": "Informe a cidade onde você atende.",
    "state": "Informe a UF onde você atende.",
    "specialty": "Informe sua especialidade principal.",
    "categories": "Escolha pelo menos uma área de atuação.",
    "attendance_modalities": "Diga como você atende.",
    "bio": f"Escreva sua apresentação com pelo menos {BIO_MIN_LENGTH} caracteres.",
}

BUSINESS_REQUIREMENT_LABELS = {
    "name": "Informe o nome do estabelecimento.",
    "category": "Escolha o tipo de estabelecimento.",
    "location": "Informe cidade e UF.",
    "operation_mode": "Diga como o estabelecimento atende.",
    "business_address": "Informe o endereço comercial.",
    "business_hours_mode": "Defina o funcionamento: sob agendamento ou horários fixos.",
    "business_hours": "Informe horários de funcionamento válidos.",
    "description": "Escreva a apresentação do estabelecimento.",
    "commercial_contact": "Informe telefone ou e-mail comercial.",
}

PROFESSIONAL_STEPS = (
    ("identity", "Nome profissional", ("display_name",)),
    ("location", "Onde você atende", ("city", "state")),
    ("specialty", "Especialidade", ("specialty", "categories")),
    ("modality", "Como você atende", ("attendance_modalities",)),
    ("presentation", "Apresentação", ("bio",)),
)

BUSINESS_STEPS = (
    ("basics", "Nome, tipo e cidade", ("name", "category", "location")),
    ("operation", "Como o estabelecimento atende", ("operation_mode",)),
    ("address", "Endereço comercial", ("business_address",)),
    ("hours", "Funcionamento", ("business_hours_mode", "business_hours")),
    ("contact", "Apresentação e contato", ("description", "commercial_contact")),
)

OPTIONAL_STEP = "personalize"
REVIEW_STEP = "review"


def _filled(value):
    return isinstance(value, str) and bool(value.strip())


def professional_missing_requirements(profile):
    """Requisitos de publicação Profissional ainda ausentes (DEC-ID-093)."""
    requirements = profile.publication_requirements
    missing = [key for key in ("display_name", "city", "state", "specialty", "categories")
               if not requirements[key]]
    modalities = {
        value.strip()
        for value in (profile.attendance_modalities or "").split(",")
        if value.strip()
    }
    if not modalities or not modalities.issubset(PROFESSIONAL_MODALITIES):
        missing.append("attendance_modalities")
    if len((profile.bio or "").strip()) < BIO_MIN_LENGTH:
        missing.append("bio")
    return missing


def _steps(definitions, missing, *, applicable=None):
    applicable = applicable or {}
    steps = []
    for key, label, requirement_keys in definitions:
        is_applicable = applicable.get(key, True)
        steps.append({
            "key": key,
            "label": label,
            "required": True,
            "applicable": is_applicable,
            "complete": (not is_applicable) or not any(item in missing for item in requirement_keys),
        })
    return steps


def _journey(*, steps, optional_complete, missing, labels, profile_complete,
             completion, published):
    steps = [
        *steps,
        {"key": OPTIONAL_STEP, "label": "Fotos e detalhes", "required": False,
         "applicable": True, "complete": optional_complete},
        {"key": REVIEW_STEP, "label": "Revisar e publicar", "required": True,
         "applicable": True, "complete": published},
    ]
    registration_complete = not missing
    current = next(
        (step["key"] for step in steps
         if step["required"] and step["applicable"] and not step["complete"]),
        REVIEW_STEP,
    )
    return {
        "steps": steps,
        "currentStep": current,
        "registrationComplete": registration_complete,
        "readyToPublish": registration_complete,
        "profileComplete": profile_complete,
        "profileCompletion": completion,
        "published": published,
        "missingRequirements": [
            {"key": key, "message": labels[key]} for key in missing
        ],
    }


def professional_journey(profile):
    missing = professional_missing_requirements(profile)
    return _journey(
        steps=_steps(PROFESSIONAL_STEPS, missing),
        optional_complete=bool(
            profile.avatar_url or profile.cover_url or profile.portfolio_items
            or _filled(profile.instagram) or _filled(profile.phone)
        ),
        missing=missing,
        labels=PROFESSIONAL_REQUIREMENT_LABELS,
        profile_complete=profile.profile_completion == 100,
        completion=profile.profile_completion,
        published=bool(profile.is_active),
    )


def business_journey(establishment):
    readiness = evaluate_establishment_readiness(establishment)
    missing = list(readiness.missing_requirements)
    return _journey(
        steps=_steps(
            BUSINESS_STEPS,
            missing,
            applicable={"address": establishment.operation_mode in PHYSICAL_MODES},
        ),
        optional_complete=bool(
            establishment.logo_url or establishment.cover_url
            or establishment.gallery_items
        ),
        missing=missing,
        labels=BUSINESS_REQUIREMENT_LABELS,
        profile_complete=readiness.percentage == 100,
        completion=readiness.percentage,
        published=bool(establishment.is_active),
    )
