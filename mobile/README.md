# IDDUN Mobile

Aplicativo React Native / Expo SDK 57 / Expo Router / TypeScript. O backend Flask neste repositório é a fonte de verdade para contas, serviços publicados, disponibilidade e reservas.

## Executar localmente

```bash
cd mobile
npm ci
npm run typecheck
npm run lint
npm start
```

Em aparelho físico, configure `EXPO_PUBLIC_API_URL` com um endereço do Flask acessível pelo dispositivo. Por padrão, o cliente usa `https://iddun-web.onrender.com`. `EXPO_PUBLIC_WEB_URL` permite definir um host web diferente.

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
