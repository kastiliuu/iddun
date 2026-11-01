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
