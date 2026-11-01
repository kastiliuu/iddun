"""Ajudante de testes: percorre o cadastro Profissional por etapas no Web.

Substitui o antigo POST único em /pro/onboarding, que publicava direto.
Cada etapa é enviada como o navegador faria; a publicação é explícita.
"""

DEFAULT_BIO = (
    "Profissional com experiência em atendimento personalizado, "
    "técnica cuidadosa e acabamento de qualidade."
)


def complete_professional_onboarding(
    client,
    *,
    display_name="Profissional Teste",
    city="Curitiba",
    state="PR",
    primary_specialty="Nail designer",
    categories=("unhas",),
    modalities=("own_space",),
    bio=DEFAULT_BIO,
    headline="",
    phone="",
    instagram="",
    whatsapp_enabled=True,
    visual_theme="beauty",
    avatar=None,
    cover=None,
    portfolio=(),
    avatar_focus=(50, 50),
    cover_focus=(50, 50),
    publish=True,
):
    steps = [
        ("nome", {"display_name": display_name}),
        ("cidade", {"city": city, "state": state}),
        ("especialidade", {
            "primary_specialty": primary_specialty,
            "categories": list(categories),
        }),
        ("atendimento", {"attendance_modalities": list(modalities)}),
        ("apresentacao", {"bio": bio, "headline": headline}),
    ]
    for slug, data in steps:
        response = client.post(f"/pro/onboarding/{slug}", data=data)
        assert response.status_code == 302, (slug, response.get_data(as_text=True)[:2000])

    photos = {
        "phone": phone,
        "instagram": instagram,
        "visual_theme": visual_theme,
        "avatar_focus_x": str(avatar_focus[0]),
        "avatar_focus_y": str(avatar_focus[1]),
        "cover_focus_x": str(cover_focus[0]),
        "cover_focus_y": str(cover_focus[1]),
    }
    if whatsapp_enabled:
        photos["whatsapp_enabled"] = "y"
    if avatar is not None:
        photos["avatar_file"] = avatar
    if cover is not None:
        photos["cover_file"] = cover
    if portfolio:
        photos["portfolio_files"] = list(portfolio)
    response = client.post(
        "/pro/onboarding/fotos",
        data=photos,
        content_type="multipart/form-data",
    )
    assert response.status_code == 302, response.get_data(as_text=True)[:2000]

    if not publish:
        return response
    response = client.post("/pro/onboarding/revisar", data={})
    assert response.status_code == 302, response.get_data(as_text=True)[:2000]
    assert response.headers["Location"].endswith("/pro/onboarding/concluido")
    return response


BUSINESS_DESCRIPTION = (
    "Um espaço dedicado a experiências de beleza, atendimento "
    "e transformação com cuidado."
)


def complete_business_onboarding(
    client,
    *,
    name="Studio Teste",
    category="salao",
    city="Curitiba",
    state="PR",
    operation_mode="physical",
    address_line1="Rua Teste, 100",
    address_line2="",
    neighborhood="",
    postal_code="",
    hours_mode="scheduled",
    hours=None,
    description=BUSINESS_DESCRIPTION,
    phone="41988888888",
    email="",
    instagram="",
    logo=None,
    cover=None,
    gallery=(),
    logo_focus=(50, 50),
    cover_focus=(50, 50),
    publish=True,
):
    """Percorre o cadastro de Estabelecimento por etapas; devolve o id."""
    response = client.post("/business/onboarding/novo", data={
        "name": name, "category": category, "city": city, "state": state,
    })
    assert response.status_code == 302, response.get_data(as_text=True)[:2000]
    location = response.headers["Location"]
    establishment_id = int(location.rstrip("/").split("/")[-2])

    def post(slug, data, **kwargs):
        result = client.post(f"/business/onboarding/{establishment_id}/{slug}", data=data, **kwargs)
        assert result.status_code == 302, (slug, result.get_data(as_text=True)[:2000])
        return result

    post("atendimento", {"operation_mode": operation_mode})
    if operation_mode in {"physical", "hybrid"}:
        post("endereco", {
            "address_line1": address_line1, "address_line2": address_line2,
            "neighborhood": neighborhood, "postal_code": postal_code,
        })
    hours_data = {"business_hours_mode": hours_mode}
    for day, (start, end) in (hours or {}).items():
        hours_data[f"{day}_start"] = start
        hours_data[f"{day}_end"] = end
    post("funcionamento", hours_data)
    post("contato", {
        "description": description, "phone": phone, "email": email,
        "instagram": instagram, "whatsapp_enabled": "y",
    })
    media = {
        "logo_focus_x": str(logo_focus[0]), "logo_focus_y": str(logo_focus[1]),
        "cover_focus_x": str(cover_focus[0]), "cover_focus_y": str(cover_focus[1]),
    }
    if logo is not None:
        media["logo_file"] = logo
    if cover is not None:
        media["cover_file"] = cover
    if gallery:
        media["gallery_files"] = list(gallery)
    post("fotos", media, content_type="multipart/form-data")
    if publish:
        result = post("revisar", {})
        assert result.headers["Location"].endswith(f"/business/onboarding/{establishment_id}/concluido")
    return establishment_id
