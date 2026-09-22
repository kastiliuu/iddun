# IDDUN — Sprint 7.1 Hotfix QA

Data: 16/09/2026

Correções desta revisão:

1. Experiências/Admin: normalização dos botões `Editar` e `Pausar/Publicar` para mesma altura, largura mínima, tipografia e alinhamento.
2. Experiência/Edit: campo de antecedência específica deixa de parecer valor perdido. Quando vazio, exibe `Usar padrão` e informa qual antecedência do profissional será herdada.
3. Experiência/Edit: corrigido `NameError: uploaded_image is not defined`. O upload agora é inicializado e validado dentro da rota correta antes de ser usado.
4. Vínculos/Edit: removido bloco de upload de experiência que havia sido inserido por engano na rota de edição de vínculo e poderia causar regressão adicional.
5. Cobertura de regressão adicionada para edição de experiência sem reupload, ajuda de cutoff herdado e edição de vínculo.

Validação estática no pacote:
- Python compileall: OK
- 36 templates Jinja: parse OK
- JavaScript: node --check OK

Observação: a suíte pytest deve ser executada no ambiente local do projeto, onde as dependências Flask estão instaladas.
