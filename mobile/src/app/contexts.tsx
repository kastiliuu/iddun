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
 * Troca de contexto pelo avatar (PR 1; DEC-ID-077, FE-DEC-022). Lista só os
 * contextos que o backend devolve em /auth/me para esta conta.
 */

export function contextSubtitle(item: AccountContext) {
  if (item.kind === "client") return "Feed, Explorar, Reservas e Favoritos";
  const state =
    item.state === "draft"
      ? " · rascunho"
      : item.state === "locked"
        ? " · fora do ar"
        : "";
  if (item.kind === "professional") return `Profissional${state}`;
  return `${item.role === "owner" ? "Proprietário" : "Gestão"}${state}`;
}

export default function ContextsScreen() {
  useStoreVersion();
  const router = useRouter();
  const user = store.getUser();

  useEffect(() => {
    // Atualiza a lista; uma falha de rede mantém a última conhecida.
    getCurrentUser().catch(() => {});
  }, []);

  const contexts: AccountContext[] =
    user?.contexts && user.contexts.length > 0
      ? user.contexts
      : user
        ? [{ kind: "client", name: user.name }]
        : [];

  const open = (item: AccountContext) => {
    if (item.kind === "client") {
      router.replace("/(tabs)");
      return;
    }
    if (item.kind === "professional") {
      router.push("/context/professional");
      return;
    }
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
      title="Trocar de contexto"
      description={user
        ? `${user.name} · uma conta pessoal. O login começa na experiência Cliente; use as ferramentas profissionais e empresariais conforme seus acessos.`
        : "Uma conta pessoal. O login começa na experiência Cliente."}
    >
      <ContextSection label="CONTA PESSOAL E TRABALHO">
        {contexts.filter((item) => item.kind !== "establishment").map((item) => (
          <ContextRow
            key={item.kind}
            icon={item.kind === "client" ? "compass" : "briefcase"}
            title={item.kind === "client" ? "Experiência Cliente" : "Painel profissional"}
            subtitle={contextSubtitle(item)}
            current={item.kind === "client"}
            onPress={() => open(item)}
          />
        ))}
      </ContextSection>

      {contexts.some((item) => item.kind === "establishment") ? (
        <ContextSection label="MEUS ESTABELECIMENTOS">
          {contexts.filter((item) => item.kind === "establishment").map((item) => (
            <ContextRow
              key={`establishment-${item.id}`}
              icon="home"
              title={item.name}
              subtitle={contextSubtitle(item)}
              onPress={() => open(item)}
            />
          ))}
        </ContextSection>
      ) : null}

      {!contexts.some((item) => item.kind === "professional") ? (
        <ContextSection label="COMEÇAR">
          <ContextRow
            icon="plus"
            title="Criar perfil profissional ou estabelecimento"
            subtitle="Cadastro por etapas, publicado só quando você quiser"
            onPress={() => router.push("/signup-pro")}
          />
        </ContextSection>
      ) : null}
    </ContextScreen>
  );
}
