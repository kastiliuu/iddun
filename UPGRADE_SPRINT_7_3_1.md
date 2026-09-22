# Upgrade — Sprint 7.3.1 Visual Rebalance

Não há migration nesta sprint.

1. Preserve `.env` e `.venv`.
2. Substitua os arquivos do projeto pela versão desta entrega.
3. Ative o ambiente virtual.
4. Rode:

```powershell
pip install -r requirements.txt
pytest -q
python run.py
```

## QA recomendado
Validar Home em:
- 1920×1080
- 1366×768
- 1024×768
- 768×1024
- 430×932
- 390×844
- 320×608

Foco do QA:
- headline e busca na primeira dobra;
- equilíbrio entre copy e demonstração de produto;
- scroll-snap mobile;
- ausência de overflow horizontal;
- CTAs e touch targets;
- ritmo entre seções;
- comportamento de motion com `prefers-reduced-motion`.
