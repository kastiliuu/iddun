import React from "react";
import { useRouter } from "expo-router";

import {
  ContextRow,
  ContextScreen,
  ContextSection,
} from "@/components/navigation/ContextScreen";
import { store, useStoreVersion } from "@/store/local";

/**
 * Contexto Profissional no app (PR 1, D-SOC-04). O app ainda não tem Painel
 * nem Clientes do Pro; esta tela reúne só as ferramentas que já existem.
 */
export default function ProfessionalContextScreen() {
  useStoreVersion();
  const router = useRouter();
  const user = store.getUser();
  const context = user?.contexts?.find((item) => item.kind === "professional");
  const draft = context?.state === "draft";
  const locked = context?.state === "locked";

  return (
    <ContextScreen
      eyebrow="CONTEXTO PROFISSIONAL"
      title={context?.name ?? "Seu trabalho no IDDUN"}
      description="Perfil, serviços, horários e vínculos. Painel e carteira de clientes estão no site por enquanto."
      notice={
        locked
          ? "Este perfil foi desativado e não pode ser publicado por aqui. Fale com o suporte do IDDUN."
          : undefined
      }
    >
      <ContextSection label="PERFIL">
        {draft ? (
          <ContextRow
            icon="edit-3"
            title="Continuar cadastro"
            subtitle="Seu perfil ainda não está no ar"
            onPress={() => router.push("/pro-onboarding")}
          />
        ) : (
          <ContextRow
            icon="edit-3"
            title="Editar perfil e portfólio"
            subtitle="Fotos, apresentação e experiência"
            onPress={() => router.push("/professional-onboarding")}
          />
        )}
        {context?.state === "published" && context.slug ? (
          <ContextRow
            icon="user"
            title="Ver perfil público"
            onPress={() =>
              router.push({
                pathname: "/professional/[id]",
                params: { id: context.slug as string },
              })
            }
          />
        ) : null}
      </ContextSection>

      <ContextSection label="ATENDIMENTO">
        <ContextRow
          icon="scissors"
          title="Serviços"
          subtitle="Criar, editar, publicar e pausar"
          onPress={() => router.push("/manage-services")}
        />
        <ContextRow
          icon="clock"
          title="Horários da semana"
          onPress={() => router.push("/weekly-schedule")}
        />
        <ContextRow
          icon="image"
          title="Publicar um trabalho"
          onPress={() => router.push("/create-post")}
        />
      </ContextSection>

      <ContextSection label="REDE E VAGAS">
        <ContextRow
          icon="users"
          title="Convites de equipe"
          subtitle="Aceite só onde você atende"
          onPress={() => router.push("/team-invitations")}
        />
        <ContextRow
          icon="briefcase"
          title="Vagas"
          onPress={() => router.push("/jobs")}
        />
        <ContextRow
          icon="send"
          title="Minhas candidaturas"
          onPress={() => router.push("/job-applications")}
        />
      </ContextSection>
    </ContextScreen>
  );
}
