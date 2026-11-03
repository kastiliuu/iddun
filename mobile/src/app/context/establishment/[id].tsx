import React from "react";
import { useLocalSearchParams, useRouter } from "expo-router";

import {
  ContextRow,
  ContextScreen,
  ContextSection,
} from "@/components/navigation/ContextScreen";
import { EmptyState } from "@/components/EmptyState";
import { store, useStoreVersion } from "@/store/local";

/**
 * Contexto de um estabelecimento no app (PR 1, D-SOC-04). Mostra as
 * ferramentas que já existem; Painel e Agenda da empresa estão no site.
 */
export default function EstablishmentContextScreen() {
  useStoreVersion();
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();
  const user = store.getUser();
  const context = user?.contexts?.find(
    (item) => item.kind === "establishment" && item.id === params.id,
  );

  if (!context?.id) {
    return (
      <ContextScreen eyebrow="ESTABELECIMENTO" title="Contexto indisponível">
        <EmptyState
          title="Você não tem acesso a este estabelecimento."
          description="Volte e escolha um dos contextos da sua conta."
          actionLabel="Trocar de contexto"
          onActionPress={() => router.replace("/contexts")}
        />
      </ContextScreen>
    );
  }

  const id = context.id;
  const owner = context.role === "owner";
  const draft = context.state === "draft";

  return (
    <ContextScreen
      eyebrow={owner ? "ESTABELECIMENTO · PROPRIETÁRIO" : "ESTABELECIMENTO · GESTÃO"}
      title={context.name}
      description="Equipe, vagas e publicações. Painel, agenda e indicadores da empresa estão no site por enquanto."
    >
      {draft && owner ? (
        <ContextSection label="CADASTRO">
          <ContextRow
            icon="edit-3"
            title="Continuar cadastro"
            subtitle="A página ainda não está no ar"
            onPress={() =>
              router.push({ pathname: "/business-onboarding", params: { id } })
            }
          />
        </ContextSection>
      ) : null}

      <ContextSection label="EQUIPE E VAGAS">
        <ContextRow
          icon="users"
          title="Equipe"
          subtitle="Convites e profissionais vinculados"
          onPress={() => router.push(`/establishment-team/${id}`)}
        />
        <ContextRow
          icon="briefcase"
          title="Vagas"
          subtitle="Publicar e acompanhar candidatos"
          onPress={() => router.push(`/manage-jobs/${id}`)}
        />
      </ContextSection>

      {!draft ? (
        <ContextSection label="PRESENÇA">
          <ContextRow
            icon="image"
            title="Publicar um trabalho"
            onPress={() => router.push("/create-post")}
          />
          {context.slug ? (
            <ContextRow
              icon="external-link"
              title="Ver página pública"
              onPress={() =>
                router.push({
                  pathname: "/establishment/[id]",
                  params: { id: context.slug as string },
                })
              }
            />
          ) : null}
        </ContextSection>
      ) : null}
    </ContextScreen>
  );
}
