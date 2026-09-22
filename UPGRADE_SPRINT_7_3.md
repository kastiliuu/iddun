# Upgrade — Sprint 7.3 Visual Direction V2

1. Preserve `.env` e `.venv` da sua máquina.
2. Substitua os arquivos do projeto pela entrega da Sprint 7.3.
3. Ative a `.venv`:

```powershell
.venv\Scripts\Activate.ps1
```

4. Dependências não mudaram, mas pode confirmar:

```powershell
pip install -r requirements.txt
```

5. Não existe migration nova nesta sprint. Não é necessário `db migrate` nem `db upgrade` por causa da 7.3.
6. Rode a regressão:

```powershell
pytest -q
```

7. Rode o sistema:

```powershell
python run.py
```

## QA recomendado
- Home: 1920x1080, 1366x768, 1024x768, 768x1024, 430x932, 390x844 e 320x608.
- Marketplace: primeiro card editorial + grid restante.
- Profissionais: destaque editorial + cards restantes.
- Minha Conta: animações, navegação e formulários.
- Admin: dashboard, cards e formulários; nenhuma animação deve atrasar ação operacional.
- Ativar “reduzir movimento” no sistema operacional e confirmar que o IDDUN continua totalmente utilizável.
