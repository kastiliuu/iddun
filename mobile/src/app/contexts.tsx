import React, { useEffect } from "react";
import { useRouter } from "expo-router";

import { getCurrentUser } from "@/api/auth";
import {
  ContextRow,
  ContextScreen,
  ContextSection,
} from "@/components/navigation/ContextScreen";
import {
  type AccountContext,
  store,
  useStoreVersion,
} from "@/store/local";

/**
 * Áreas da conta pelo avatar (QA-001, 19/11). Contextos de /auth/me
 * seguem como permissões técnicas, não como identidades Cliente/Pro.
 */

export function contextSubtitle(item: AccountContext) {
  if (item.kind === "client") return "Feed, Explorar, Reservas e Favoritos";
  const state =
    item.state === "draft"
      ? " · rascunho"
      : item.state === "locked"
        ? " · fora do ar"
        : "";
  if (item.kind === "professional") return `Painel, agenda e serviços${state}`;
  return `${item.role === "owner" ? "Proprietário" : "Gestão"}${state}`;
}

export default function ContextsScreen() {
  useStoreVersion();
  const router = useRouter();
  const user = store.getUser();

  useEffect(() => {
    // Atualiza os vínculos; falha de rede não concede acessos novos.
    getCurrentUser().catch(() => {});
  }, []);

  const contexts: AccountContext[] =
    user?.contexts && user.contexts.length > 0
      ? user.contexts
      : user
        ? [{ kind: "client", name: user.name }]
        : [];
  const professional = contexts.find((item) => item.kind === "professional");
  const businesses = contexts.filter((item) => item.kind === "establishment");

  const openBusiness = (item: AccountContext) => {
    if (item.id) {
      router.push({
        pathname: "/context/establishment/[id]",
        params: { id: item.id },
      });
    }
  };

  return (
    <ContextScreen
      eyebrow="SUA CONTA"
      title="Minha conta e ferramentas"
      description={user
        ? `${user.name} · uma identidade pessoal para explorar, reservar e publicar. Ferramentas profissionais e páginas de estabelecimentos são recursos desta mesma conta.`
        : "Uma identidade pessoal para todas as atividades no IDDUN."}
    >
      <ContextSection label="CONTA PESSOAL">
        <ContextRow
          icon="user"
          title="Meu feed e perfil"
          subtitle="Explorar, publicar, seguir e reservar com a mesma identidade"
          onPress={() => router.replace("/(tabs)")}
        />
      </ContextSection>

      <ContextSection label="FERRAMENTAS DE TRABALHO">
        {professional ? (
          <ContextRow
            icon="briefcase"
            title="Ferramentas profissionais"
            subtitle={contextSubtitle(professional)}
            onPress={() => router.push("/context/professional")}
          />
        ) : (
          <ContextRow
            icon="briefcase"
            title="Ativar atuação profissional"
            subtitle="Adicione recursos de trabalho à sua conta pessoal"
            onPress={() => router.push("/signup-pro")}
          />
        )}
        <ContextRow
          icon="home"
          title="Criar estabelecimento"
          subtitle="Páginas institucionais com identidade e permissões próprias"
          onPress={() => router.push({
            pathname: "/signup-pro",
            params: { accountType: "establishment" },
          })}
        />
      </ContextSection>

      {businesses.length > 0 ? (
        <ContextSection label="MEUS ESTABELECIMENTOS">
          {businesses.map((item) => (
            <ContextRow
              key={`establishment-${item.id}`}
              icon="home"
              title={item.name}
              subtitle={contextSubtitle(item)}
              onPress={() => openBusiness(item)}
            />
          ))}
        </ContextSection>
      ) : null}
    </ContextScreen>
  );
}
