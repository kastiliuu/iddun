"""Escrita da mídia de identidade pessoal única (QA-001; Notion 08).

Os modelos ClientProfile e ProfessionalProfile seguem existindo: são
espelhos de compatibilidade, não contas distintas. Chamar o helper na mesma
transação/UploadBatch do gravador existente. Não apagar imagens de origem
durante o rollout; media_maintenance avalia referências ao coletar órfãos.
"""


def set_personal_avatar(user, value):
    """Persiste a única foto da pessoa e espelha para leitores legados.

    Não faz commit: o chamador deve salvar tudo ou nada na transação.
    """
    user.avatar_url = value
    if user.client_profile is not None:
        user.client_profile.avatar_url = value
    if user.professional_profile is not None:
        user.professional_profile.avatar_url = value


def set_personal_cover(user, value):
    """Persiste a capa pessoal e espelha o campo Pro anterior."""
    user.cover_url = value
    if user.professional_profile is not None:
        user.professional_profile.cover_url = value
