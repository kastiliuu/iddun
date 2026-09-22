# Upgrade — Sprint 7.4 Home V3

A Sprint 7.4 altera apenas a apresentação da Home e adiciona um asset otimizado para o hero. Não há alteração de banco nem migration.

## Aplicar

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python run.py
```

## QA recomendado

Desktop:
- 1920×1080
- 1440×900
- 1366×768
- 1024×768

Mobile:
- 430×932
- 390×844
- 375×812
- 320×568

## Pontos de QA
- Home deve exibir somente um campo de busca visível.
- Hero não pode gerar overflow horizontal.
- Retrato deve permanecer à direita no desktop.
- CTA e busca devem continuar legíveis em 1366×768.
- Glow/light trails não podem bloquear cliques (`pointer-events: none`).
- Em `prefers-reduced-motion`, animações decorativas devem ser desligadas.
- Cards devem manter tamanhos consistentes mesmo com imagens de proporções diferentes.
- No mobile, experiências e profissionais usam trilhos horizontais com scroll-snap.
