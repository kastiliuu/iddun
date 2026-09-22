# IDDUN · Sprint 7.2 — UI Consistency + Media Focus Hotfix

## Objetivo
Corrigir os bugs levantados no QA após a Sprint 7/7.1:

- steppers numéricos desalinhados;
- ações `Editar` / `Pausar` com caixas diferentes;
- imagens reais mudando a composição dos cards;
- falta de controle de enquadramento de fotos de profissionais e experiências.

## Atualização
Preserve `.env` e `.venv`, copie os arquivos da entrega e execute:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app run.py db upgrade
pytest -q
python run.py
```

A migration desta entrega adiciona apenas metadados de enquadramento (0–100%) a profissionais e experiências; imagens existentes recebem centro `50/50`.

## Media Focus
A foto original continua armazenada. O IDDUN salva um ponto focal X/Y que é usado por todos os cards com `object-fit: cover`. No Admin, o usuário pode tocar/clicar/arrastar a prévia para escolher a região principal da imagem sem permitir que o tamanho original altere o card.
