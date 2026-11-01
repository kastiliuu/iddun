// Entrada do cadastro profissional e de estabelecimento no app.
// Onboarding V0 (PRs 2 e 3): os dois cadastros acontecem por etapas, salvas
// no servidor, nas telas /pro-onboarding e /business-onboarding — a mesma
// ordem e as mesmas regras do Web. Esta tela só ajuda a escolher e a
// retomar rascunhos.
import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";

import {
  type EstablishmentDraft,
  getProfessionalOnboarding,
  listEstablishmentDrafts,
} from "@/api/onboarding";
import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import { fonts, makeStyles, radius, spacing, touch, useTheme } from "@/theme";

type AccountType = "professional" | "establishment";
type ProfessionalState = "none" | "draft" | "published" | "locked";

export default function SignupProfessionalScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [accountType, setAccountType] = useState<AccountType>("professional");
  const [professional, setProfessional] = useState<ProfessionalState>("none");
  const [drafts, setDrafts] = useState<EstablishmentDraft[]>([]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      // Uma falha de rede só esconde a retomada; começar continua possível.
      try {
        const response = await getProfessionalOnboarding();
        if (mounted && response.profile) {
          // publishedAt sem isActive: desativado pela moderação.
          setProfessional(
            response.profile.isActive ? "published" : response.profile.publishedAt ? "locked" : "draft",
          );
        }
      } catch {}
      try {
        const response = await listEstablishmentDrafts();
        if (mounted) {
          setDrafts(response.establishments.filter((item) => !item.isActive && !item.publishedAt));
        }
      } catch {}
    };
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  const choose = (value: AccountType) => {
    Haptics.selectionAsync().catch(() => {});
    setAccountType(value);
  };

  const typeCard = (value: AccountType, icon: "user" | "home", title: string, body: string) => {
    const selected = accountType === value;
    return (
      <Pressable
        accessibilityRole="radio"
        accessibilityState={{ checked: selected }}
        onPress={() => choose(value)}
        style={({ pressed }) => [styles.typeCard, selected && styles.typeCardSelected, pressed && styles.pressed]}
      >
        <View style={styles.typeIcon}>
          <Icon name={icon} size={20} color={selected ? colors.plum : colors.muted} />
        </View>
        <Text style={styles.typeTitle}>{title}</Text>
        <Text style={styles.typeDescription}>{body}</Text>
      </Pressable>
    );
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => (router.canGoBack() ? router.back() : router.replace("/(tabs)/profile"))}
            style={({ pressed }) => [styles.headerButton, pressed && styles.pressed]}
          >
            <Icon name="arrow-left" size={20} color={colors.onSurface} />
          </Pressable>
          <Image
            source={require("../../../assets/branding/iddun-logo-white.png")}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />
          <View style={styles.headerPlaceholder} />
        </View>

        <Text style={styles.eyebrow}>IDDUN PROFISSIONAL</Text>
        <Text style={styles.title} accessibilityRole="header">Transforme seu trabalho em presença.</Text>
        <Text style={styles.description}>
          Crie seu perfil profissional ou a página do seu espaço. Uma pergunta por vez, tudo salvo para você
          continuar depois.
        </Text>

        <Text style={styles.fieldLabel}>Como você trabalha?</Text>
        <View style={styles.typeOptions} accessibilityRole="radiogroup">
          {typeCard("professional", "user", "Profissional", "Trabalho de forma independente ou dentro de um espaço.")}
          {typeCard("establishment", "home", "Estabelecimento", "Salão, studio, barbearia, clínica ou outro espaço com equipe.")}
        </View>

        {accountType === "professional" ? (
          <View style={styles.entry}>
            <Text style={styles.entryTitle}>
              {professional === "locked"
                ? "Seu perfil profissional foi desativado."
                : professional === "published"
                  ? "Seu perfil profissional já está no ar."
                : professional === "draft"
                  ? "Você tem um cadastro profissional em andamento."
                  : "Cadastro em 7 etapas curtas."}
            </Text>
            <Text style={styles.entryText}>
              {professional === "locked"
                ? "Não é possível publicar por aqui. Fale com o suporte do IDDUN."
                : professional === "published"
                  ? "Para mudar fotos, portfólio ou apresentação, use o editor do seu perfil."
                : "Cada etapa fica salva e você publica quando estiver tudo pronto."}
            </Text>
            {professional !== "locked" ? (
              <Button
                title={
                  professional === "published"
                    ? "Editar meu perfil"
                    : professional === "draft"
                      ? "Continuar cadastro"
                      : "Começar cadastro profissional"
                }
                fullWidth
                onPress={() => router.push(professional === "published" ? "/professional-onboarding" : "/pro-onboarding")}
              />
            ) : null}
          </View>
        ) : (
          <View style={styles.entry}>
            {drafts.length > 0 ? (
              <>
                <Text style={styles.entryTitle}>Continue de onde parou</Text>
                {drafts.map((item) => (
                  <Pressable
                    key={item.id}
                    accessibilityRole="button"
                    onPress={() => router.push({ pathname: "/business-onboarding", params: { id: item.id } })}
                    style={({ pressed }) => [styles.draft, pressed && styles.pressed]}
                  >
                    <View style={styles.draftText}>
                      <Text style={styles.draftTitle}>Continuar {item.name}</Text>
                      <Text style={styles.entryText}>
                        {item.city}/{item.state} · rascunho, ainda não publicado
                      </Text>
                    </View>
                    <Icon name="chevron-right" size={18} color={colors.muted} />
                  </Pressable>
                ))}
              </>
            ) : (
              <Text style={styles.entryTitle}>Cadastro em 7 etapas curtas.</Text>
            )}
            <Text style={styles.entryText}>
              Nome, tipo e cidade criam o rascunho. A página só vai ao ar quando você publicar.
            </Text>
            <Button
              title={drafts.length > 0 ? "Criar outro estabelecimento" : "Começar cadastro do estabelecimento"}
              variant={drafts.length > 0 ? "outline" : "primary"}
              fullWidth
              onPress={() => router.push("/business-onboarding")}
            />
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingTop: 54, paddingHorizontal: spacing.lg, paddingBottom: spacing.xxxl },
  header: { minHeight: 52, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  headerButton: {
    width: touch.minimum,
    height: touch.minimum,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.glassSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  headerPlaceholder: { width: touch.minimum, height: touch.minimum },
  logo: { width: 104, height: 32 },
  eyebrow: { marginTop: spacing.xl, color: colors.plum, fontFamily: fonts.sansMedium, fontSize: 12, letterSpacing: 1.5 },
  title: {
    maxWidth: 350,
    marginTop: spacing.sm,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 32,
    lineHeight: 38,
  },
  description: {
    maxWidth: 340,
    marginTop: spacing.md,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 14,
    lineHeight: 21,
  },
  fieldLabel: { marginTop: spacing.xxl, color: colors.onSurfaceSecondary, fontFamily: fonts.sansMedium, fontSize: 13 },
  typeOptions: { marginTop: spacing.sm, gap: spacing.sm },
  typeCard: {
    minHeight: 112,
    padding: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  typeCardSelected: { backgroundColor: colors.plumSoft, borderColor: colors.plum },
  typeIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.glassSoft,
  },
  typeTitle: { marginTop: spacing.md, color: colors.onSurface, fontFamily: fonts.sansSemiBold, fontSize: 15 },
  typeDescription: { marginTop: spacing.xs, color: colors.muted, fontFamily: fonts.sans, fontSize: 12, lineHeight: 17 },
  entry: { marginTop: spacing.xxl, gap: spacing.md },
  entryTitle: { color: colors.onSurface, fontFamily: fonts.sansSemiBold, fontSize: 16 },
  entryText: { color: colors.muted, fontFamily: fonts.sans, fontSize: 13, lineHeight: 19 },
  draft: {
    minHeight: 64,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    backgroundColor: colors.surfaceSecondary,
  },
  draftText: { flex: 1, gap: 2 },
  draftTitle: { color: colors.onSurface, fontFamily: fonts.sansSemiBold, fontSize: 14 },
  pressed: { opacity: 0.75 },
}));
