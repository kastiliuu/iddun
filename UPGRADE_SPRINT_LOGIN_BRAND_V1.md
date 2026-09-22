# Sprint — Login na identidade oficial IDDUN

## Objetivo

Atualizar a experiência visual do login para a identidade Ink, Graphite, Mist,
Electric Plum e Deep Violet, preservando o fluxo Flask existente.

## Alterações entregues

- Login redesenhado sem cores douradas.
- CTA principal com gradiente Electric Plum para Deep Violet.
- Fundo editorial com glows assimétricos e textura leve.
- Logo oficial aplicada no login, cadastro, header e footer da Home.
- Card de prova social com superfície Graphite, borda Plum e aspas editoriais.
- Inputs Graphite com ícones e foco Plum.
- Checkbox customizado em Plum.
- Mostrar/ocultar senha com ícones, texto, `aria-label` e `aria-pressed`.
- Estados de hover, foco, active, disabled e loading.
- Mensagens de erro com vermelho acessível e indicação textual.
- Layout responsivo usando `100dvh` e identidade compacta no mobile.
- Suporte a `prefers-reduced-motion`.
- Correção do loading preservado ao voltar pelo histórico do navegador.

## Arquivos principais

- `app/templates/auth/login.html`
- `app/templates/auth/register.html`
- `app/static/css/auth.css`
- `app/static/js/auth.js`
- `app/templates/components/header.html`
- `app/templates/components/footer.html`
- `app/static/css/components.css`
- `app/static/css/home.css`

## Funcionalidades preservadas

- Autenticação Flask real.
- CSRF.
- Redirecionamento seguro por `next`.
- Continuar conectado.
- Validação no cliente e no servidor.
- Erro geral para credenciais inválidas ou conta desativada.
- Bloqueio de envio duplicado.
- Avisos para integrações Google, Apple e recuperação ainda indisponíveis.

## Validações executadas

- Sintaxe JavaScript validada com `node --check`.
- Arquivos Python compilados com `compileall`.
- Blocos CSS e delimitadores Jinja verificados.
- Busca automática confirmou ausência dos tokens dourados no login.
- Assets de logo branca e preta confirmados no pacote.

## Observação

Os botões Google, Apple e “Esqueci minha senha” continuam comunicando que a
integração está em preparação, como já acontecia. Nenhum login fictício foi
criado nesta sprint.
