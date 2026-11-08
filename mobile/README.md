# IDDUN Mobile

Aplicativo React Native / Expo SDK 58 / Expo Router / TypeScript. O backend Flask neste repositório é a fonte de verdade para contas, serviços publicados, disponibilidade e reservas.

## Executar localmente

```bash
cd mobile
npm ci
npm run typecheck
npm run lint
npm start
```

### Homologação com iPhone/Android e Flask local

O comando `npm start` continua usando a API padrão do cliente, `https://iddun-web.onrender.com`, quando `EXPO_PUBLIC_API_URL` não está definido. **Se você está rodando Flask no Windows, use `npm run start:local` em vez de `npm start`**. Esse comando verifica `/health` em loopback e na interface LAN antes de abrir o Expo e injeta `EXPO_PUBLIC_API_URL` somente no processo filho (não grava segredos nem modifica `.env`).

1. Na raiz do repositório, ative o ambiente Python **da raiz**, não `mobile/.venv`:

   ```powershell
   cd "C:\caminho\para\iddun-master"
   .\.venv\Scripts\Activate.ps1
   python -m flask --app app run --host 0.0.0.0 --port 5000
   ```

2. Em **outra janela** do PowerShell, com o backend rodando e o iPhone na mesma rede Wi-Fi:

   ```powershell
   cd mobile
   npm ci
   npm run start:local
   ```

3. Se houver várias interfaces locais (VPN, WSL, Ethernet e Wi-Fi), escolha explicitamente o IPv4 da rede do iPhone (verifique com `ipconfig`):

   ```powershell
   $env:IDDUN_LAN_IP="192.168.0.8" # exemplo; use seu IP real
   npm run start:local
   ```

4. No Safari do iPhone abra `http://SEU_IPV4:5000/health` e confirme `{"status":"ok"}` antes de testar login, feed e reservas no Expo Go. Se falhar: mesma rede, endereço correto, Flask vinculado a `0.0.0.0` e firewall do Windows liberando a porta **somente na rede privada**. Não desative o firewall.

A porta padrão é 5000; use `IDDUN_BACKEND_PORT` se o Flask estiver em outra porta. `npm run test:local` executa testes unitários isolados do inicializador sem precisar do backend. `EXPO_PUBLIC_WEB_URL` permite definir host Web diferente. A verificação de `/health` comprova a acessibilidade da API naquele momento, mas **não** substitui testes de login/autorização nem homologação em aparelhos. Não exponha servidor de desenvolvimento à internet.

## Integração atual — inventário verificado em 21/10/2026

Os textos antigos que descreviam o aplicativo **inteiro** como um protótipo com reservas somente redirecionadas para a web ficaram obsoletos. Evidências atuais:

| Fluxo | Evidência de código | Limite do aceite |
| --- | --- | --- |
| Login e sessão | `src/api/auth.ts` (tokens e renovação de sessão) | Requer QA real Web × Android × iOS |
| Descoberta e busca | `src/api/experiences.ts`, `src/api/discovery.ts`, `src/api/search.ts` | Não assumir catálogo completo nem paridade visual |
| Agendamento real | `src/app/booking/[serviceId].tsx`, `src/api/bookings.ts` (hold, confirmação, leitura de reserva) | Testar conflitos HTTP 409, expiração e concorrência; aprovação em CI não equivale a homologação |
| Minhas reservas | `src/app/bookings.tsx`, `src/api/bookings.ts` | Validar permissões e ciclo de solicitação |
| Dados de demonstração | `src/mocks/data.ts` | Revisar individualmente para garantir ausência de conteúdo falso em fluxos de produção |

O backend possui endpoints em `app/routes/api_bookings.py` e rotas web em `app/routes/bookings.py`. Os clientes não devem manter regras de reserva divergentes.

## Regras aprovadas no Notion para reservas

Fonte: página **41 | Rodada 15 — Jornada de reserva aprovada**, decisões DEC-ID-109–116:
- Entrada por serviço, Pro, estabelecimento ou post, preservando contexto.
- Serviço institucional com múltiplos profissionais: escolher executor ou qualquer disponível, com atribuição antes da confirmação.
- Disponibilidade real e checada no servidor; sem criação fictícia de reservas.
- Cliente **solicita** cancelamento; somente executor **efetiva** (DEC-ID-112 e DEC-ID-022).
- Solicitação de reagendamento segue a política do serviço, sem trocar arbitrariamente um horário confirmado.
- Após confirmação, apresentar estado real e acesso a Minhas Reservas.

**A existência de funções e telas não comprova atendimento integral às decisões.** Auditoria de contratos/integração Web × Mobile e QA em dispositivos continuam pendentes.

## Comprovação mínima antes de release

1. CI: `npm ci`, `npx expo install --check`, `npm run typecheck`, `npm run lint`.
2. Fluxo real: login → descobrir serviço publicado → consultar disponibilidade → hold → confirmar → visualizar reserva.
3. Casos adversos: sem conexão, slot ocupado, hold expirado, resposta de confirmação inconclusiva, troca rápida de filtros.
4. Paridade Web × Mobile: status, mensagens, permissões, preços e cancelamento/reagendamento segundo decisão aprovada.
5. Proibir dados fictícios em fluxos de produção e documentar qualquer lacuna de QA antes da publicação.

Documentação reconciliada a partir de `main@0e9486591dace6dfda3b0aac6caeccdfae65e603`. Não é certificado de release.
