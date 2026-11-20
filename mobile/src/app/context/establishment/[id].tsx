import React from "react";
import { useLocalSearchParams, useRouter } from "expo-router";

import {
  ContextRow,
  ContextScreen,
  ContextSection,
} from "@/components/navigation/ContextScreen";
import { EmptyState } from "@/components/EmptyState";
import { store, useStoreVersion } from "@/store/local";
import { openWebEditor } from "@/components/ProfileSections";

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
          description="Volte às áreas da sua conta e selecione uma página autorizada."
          actionLabel="Ver meus estabelecimentos"
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
      contextLabel={context.name}
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

      {context.slug ? (
        <ContextSection label="GESTÃO NA WEB">
          {owner ? (
            <ContextRow
              icon="users"
              title="Permissões de recrutamento"
              subtitle="Conceder ou retirar acesso dos gestores no site"
              onPress={() => openWebEditor(`/business/${encodeURIComponent(context.slug as string)}/vagas#gerentes`)}
            />
          ) : null}
          <ContextRow
            icon="external-link"
            title="Painel do estabelecimento"
            subtitle="Gestão completa no site"
            onPress={() => openWebEditor(`/business/${encodeURIComponent(context.slug as string)}/painel`)}
          />
          {!draft ? (
            <>
              <ContextRow
                icon="scissors"
                title="Serviços do estabelecimento"
                subtitle="Catálogo e gestão dos serviços no site"
                onPress={() => openWebEditor(`/business/${encodeURIComponent(context.slug as string)}/servicos`)}
              />
              <ContextRow
                icon="calendar"
                title="Reservas da empresa"
                subtitle="Acompanhe atendimentos no site"
                onPress={() => openWebEditor(`/business/${encodeURIComponent(context.slug as string)}/reservas`)}
              />
              <ContextRow
                icon="bar-chart-2"
                title="Indicadores do estabelecimento"
                subtitle="Métricas reais no site"
                onPress={() => openWebEditor(`/business/${encodeURIComponent(context.slug as string)}/indicadores`)}
              />
            </>
          ) : null}
        </ContextSection>
      ) : null}

      {!draft ? (
        <ContextSection label="PRESENÇA">
          {/* P-004: quem é dona publica como a empresa (o Creator e o
              servidor conferem de novo); a gestão publica como pessoa. */}
          <ContextRow
            icon="image"
            title={
              owner
                ? `Publicar como ${context.name}`
                : "Publicar um trabalho"
            }
            subtitle={
              owner
                ? "A publicação sai em nome da empresa"
                : "A publicação sai no seu nome"
            }
            onPress={() =>
              owner
                ? router.push({
                    pathname: "/create-post",
                    params: { author: `establishment:${id}` },
                  })
                : router.push("/create-post")
            }
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
