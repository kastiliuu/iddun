import React, {
  useMemo,
} from "react";
import {
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";

import { Button } from "@/components/Button";
import { Icon, IconName } from "@/components/Icon";
import { openWebEditor } from "@/components/ProfileSections";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  touch,
  useTheme,
} from "@/theme";

type ActionCardProps = {
  icon: IconName;
  title: string;
  description: string;
  onPress?: () => void;
  disabled?: boolean;
  badge?: string;
};

function ActionCard({
  icon,
  title,
  description,
  onPress,
  disabled = false,
  badge,
}: ActionCardProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  const handlePress = () => {
    if (disabled || !onPress) {
      return;
    }

    Haptics.impactAsync(
      Haptics.ImpactFeedbackStyle.Light,
    ).catch(() => {});

    onPress();
  };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${description}`}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.actionCard,
        disabled && styles.actionCardDisabled,
        pressed &&
          !disabled &&
          styles.actionCardPressed,
      ]}
    >
      <View style={styles.actionIcon}>
        <Icon
          name={icon}
          size={20}
          color={colors.plum}
        />
      </View>

      <View style={styles.actionContent}>
        <View style={styles.actionTitleRow}>
          <Text
            style={styles.actionTitle}
            numberOfLines={1}
          >
            {title}
          </Text>

          {badge ? (
            <View style={styles.actionBadge}>
              <Text style={styles.actionBadgeText}>
                {badge}
              </Text>
            </View>
          ) : null}
        </View>

        <Text
          style={styles.actionDescription}
          numberOfLines={2}
        >
          {description}
        </Text>
      </View>

      <Icon
        name={disabled ? "clock" : "chevron-right"}
        size={18}
        color={colors.muted}
      />
    </Pressable>
  );
}

export default function CreateScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors, scheme } = useTheme();
  const router = useRouter();

  const user = store.getUser();

  // Contextos são recursos da mesma pessoa: o papel legado não é
  // exclusivo e não pode esconder uma empresa de quem também atua Pro.
  const contexts = user?.contexts ?? [];
  const businessContexts = contexts.filter(
    (item) => item.kind === "establishment",
  );
  const isProfessional = contexts.some(
    (item) => item.kind === "professional",
  ) || (!user?.contexts && user?.role === "professional");
  const isEstablishment =
    businessContexts.length > 0 ||
    (!user?.contexts && user?.role === "establishment");

  // Selecionar uma empresa só se for a única autorizada no menu.
  // Com múltiplas empresas, a pessoa escolhe em /contexts.
  const currentBusiness =
    businessContexts.length === 1 ? businessContexts[0] : undefined;

  const canCreate =
    isProfessional ||
    isEstablishment;

  const profileLabel = useMemo(() => {
    if (isProfessional && isEstablishment) {
      return "FERRAMENTAS PROFISSIONAIS E EMPRESARIAIS";
    }

    if (isEstablishment) {
      return "ESTABELECIMENTOS";
    }

    if (isProfessional) {
      return "FERRAMENTAS PROFISSIONAIS";
    }

    return "IDDUN PARA PROFISSIONAIS";
  }, [
    isEstablishment,
    isProfessional,
  ]);

  const handleBecomeProfessional =
    () => {
      if (!user) {
        router.push({
          pathname: "/login",
          params: {
            mode: "signup",
            accountType:
              "professional",
          },
        });

        return;
      }

      router.push(
        "/signup-pro",
      );
    };

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={
          styles.content
        }
        showsVerticalScrollIndicator={
          false
        }
      >
        <View style={styles.header}>
          <Image
            source={scheme === "light"
              ? require("../../assets/branding/iddun-logo-black.png")
              : require("../../assets/branding/iddun-logo-white.png")}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

          {/* PR 1: Criar saiu das abas; a tela agora volta para onde estava. */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Fechar"
            onPress={() =>
              router.canGoBack()
                ? router.back()
                : router.replace("/(tabs)")
            }
            style={({ pressed }) => [
              styles.headerButton,
              pressed &&
                styles.pressed,
            ]}
          >
            <Icon
              name="x"
              size={20}
              color={
                colors.onSurface
              }
            />
          </Pressable>
        </View>

        <View style={styles.hero}>
          <View
            style={styles.eyebrowRow}
          >
            <Text
              accessible={false}
              style={styles.spark}
            >
              {SPARK}
            </Text>

            <Text
              style={styles.eyebrow}
            >
              {profileLabel}
            </Text>
          </View>

          <Text style={styles.title}>
            {canCreate
              ? "Transforme seu trabalho em descoberta."
              : "Seu trabalho também pode viver no IDDUN."}
          </Text>

          <Text
            style={styles.description}
          >
            {canCreate
              ? "Publique trabalhos, divulgue horários e mantenha sua presença profissional ativa."
              : "Crie uma presença profissional, mostre seu trabalho e conecte-se com pessoas que estão procurando novas experiências."}
          </Text>
        </View>

        {!canCreate ? (
          <>
            {user ? (
              <View style={styles.section}>
                <ActionCard
                  icon="image"
                  title="Nova publicação pessoal"
                  description="Compartilhe com a sua conta pessoal, sem ativar atuação profissional."
                  onPress={() => router.push("/create-post")}
                />
              </View>
            ) : null}
            <View
              style={
                styles.becomeProfessionalCard
              }
            >
            <View
              style={
                styles.becomeIcon
              }
            >
              <Icon
                name="briefcase"
                size={24}
                color={
                  colors.plum
                }
              />
            </View>

            <Text
              style={
                styles.becomeTitle
              }
            >
              Faça parte do IDDUN
            </Text>

            <Text
              style={
                styles.becomeDescription
              }
            >
              Profissionais independentes e estabelecimentos podem criar perfil, publicar trabalhos e disponibilizar serviços.
            </Text>

            <View
              style={
                styles.becomeBenefits
              }
            >
              <View
                style={
                  styles.benefitRow
                }
              >
                <Icon
                  name="check"
                  size={15}
                  color={
                    colors.plum
                  }
                />

                <Text
                  style={
                    styles.benefitText
                  }
                >
                  Perfil profissional
                </Text>
              </View>

              <View
                style={
                  styles.benefitRow
                }
              >
                <Icon
                  name="check"
                  size={15}
                  color={
                    colors.plum
                  }
                />

                <Text
                  style={
                    styles.benefitText
                  }
                >
                  Portfólio e publicações
                </Text>
              </View>

              <View
                style={
                  styles.benefitRow
                }
              >
                <Icon
                  name="check"
                  size={15}
                  color={
                    colors.plum
                  }
                />

                <Text
                  style={
                    styles.benefitText
                  }
                >
                  Serviços e horários
                </Text>
              </View>

              <View
                style={
                  styles.benefitRow
                }
              >
                <Icon
                  name="check"
                  size={15}
                  color={
                    colors.plum
                  }
                />

                <Text
                  style={
                    styles.benefitText
                  }
                >
                  Descoberta pelo feed
                </Text>
              </View>
            </View>

            <View
              style={
                styles.ctaWrap
              }
            >
              <Button
                title="Tornar-me profissional"
                onPress={
                  handleBecomeProfessional
                }
                fullWidth
              />
            </View>
          </View>
          </>
        ) : (
          <>
            <View
              style={
                styles.profileSummary
              }
            >
              <View
                style={
                  styles.profileSummaryIcon
                }
              >
                <Icon
                  name={
                    isEstablishment
                      ? "home"
                      : "user"
                  }
                  size={19}
                  color={
                    colors.plum
                  }
                />
              </View>

              <View
                style={
                  styles.profileSummaryText
                }
              >
                <Text
                  style={
                    styles.profileSummaryName
                  }
                  numberOfLines={1}
                >
                  {user?.name}
                </Text>

                <Text
                  style={
                    styles.profileSummaryRole
                  }
                >
                  {isProfessional && isEstablishment
                    ? "Profissional e gestão de empresas"
                    : isEstablishment
                      ? "Gestão de estabelecimentos"
                      : "Profissional"}
                </Text>
              </View>

              <View
                style={
                  styles.activeBadge
                }
              >
                <View
                  style={
                    styles.activeDot
                  }
                />

                <Text
                  style={
                    styles.activeText
                  }
                >
                  Ativo
                </Text>
              </View>
            </View>

            <View
              style={
                styles.section
              }
            >
              <Text
                style={
                  styles.sectionEyebrow
                }
              >
                CRIAR
              </Text>

              <Text
                style={
                  styles.sectionTitle
                }
              >
                O que você quer fazer?
              </Text>

              <View
                style={
                  styles.actionList
                }
              >
                <ActionCard
                  icon="image"
                  title="Nova publicação"
                  description="Compartilhe um trabalho no feed do IDDUN."
                  onPress={() =>
                    router.push(
                      "/create-post",
                    )
                  }
                />

                {isProfessional ? (
                  <ActionCard
                    icon="clock"
                    title="Abrir um horário"
                    description="Publique uma disponibilidade real no IDDUN Now."
                    onPress={() =>
                      router.push("/open-slot")
                    }
                  />
                ) : null}

                {/* P-003: o catálogo do profissional já existe no app. A
                    operação da empresa fica no site neste ciclo (V1-CONV-D01). */}
                {isProfessional ? (
                  <ActionCard
                    icon="scissors"
                    title="Gerenciar serviços"
                    description="Crie, publique e abra horários dos seus serviços."
                    onPress={() => router.push("/manage-services")}
                  />
                ) : null}

                {isEstablishment ? (
                  <ActionCard
                    icon="scissors"
                    title="Serviços da empresa"
                    description="Gerencie o catálogo da empresa no site do IDDUN."
                    badge="NO SITE"
                    onPress={() =>
                      currentBusiness?.slug
                        ? openWebEditor(`/business/${encodeURIComponent(currentBusiness.slug)}/servicos`)
                        : router.push("/contexts")
                    }
                  />
                ) : null}

                {isEstablishment ? (
                  <ActionCard
                    icon="users"
                    title="Gerenciar equipe"
                    description="Organize profissionais vinculados ao estabelecimento."
                    onPress={() =>
                      currentBusiness?.id
                        ? router.push(`/establishment-team/${currentBusiness.id}`)
                        : router.push("/contexts")
                    }
                  />
                ) : null}
              </View>
            </View>

            <View
              style={
                styles.tipCard
              }
            >
              <Text
                accessible={false}
                style={
                  styles.tipSpark
                }
              >
                {SPARK}
              </Text>

              <View
                style={
                  styles.tipContent
                }
              >
                <Text
                  style={
                    styles.tipTitle
                  }
                >
                  Presença constante importa
                </Text>

                <Text
                  style={
                    styles.tipText
                  }
                >
                  Novos trabalhos, horários e serviços ajudam seu perfil a continuar relevante para quem está descobrindo o IDDUN.
                </Text>
              </View>
            </View>
          </>
        )}

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles(
  (colors) => ({
    container: {
      flex: 1,
      backgroundColor:
        colors.surface,
    },

    content: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
    },

    header: {
      minHeight: 52,

      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "space-between",
    },

    logo: {
      width: 112,
      height: 34,
    },

    headerButton: {
      width:
        touch.minimum,

      height:
        touch.minimum,

      borderRadius:
        radius.pill,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.glassSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    hero: {
      marginTop:
        spacing.xl,
    },

    eyebrowRow: {
      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,
    },

    spark: {
      color:
        colors.link,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 12,
      lineHeight: 16,
    },

    eyebrow: {
      color:
        colors.link,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 14,

      letterSpacing: 1.4,
    },

    title: {
      maxWidth: 350,

      marginTop:
        spacing.sm,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 34,
      lineHeight: 40,

      letterSpacing: -0.5,
    },

    description: {
      maxWidth: 340,

      marginTop:
        spacing.md,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 13,
      lineHeight: 20,
    },

    becomeProfessionalCard: {
      marginTop:
        spacing.xxl,

      padding:
        spacing.xl,

      borderRadius:
        radius.lg,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    becomeIcon: {
      width: 50,
      height: 50,

      borderRadius:
        radius.md,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    becomeTitle: {
      marginTop:
        spacing.lg,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 24,
      lineHeight: 30,
    },

    becomeDescription: {
      marginTop:
        spacing.sm,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 13,
      lineHeight: 19,
    },

    becomeBenefits: {
      marginTop:
        spacing.xl,

      gap: spacing.md,
    },

    benefitRow: {
      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,
    },

    benefitText: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 12,
      lineHeight: 16,
    },

    ctaWrap: {
      marginTop:
        spacing.xl,
    },

    profileSummary: {
      marginTop:
        spacing.xxl,

      minHeight: 72,

      padding:
        spacing.md,

      borderRadius:
        radius.md,

      flexDirection:
        "row",

      alignItems:
        "center",

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    profileSummaryIcon: {
      width: 42,
      height: 42,

      borderRadius:
        radius.md,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.plumSoft,
    },

    profileSummaryText: {
      flex: 1,
      minWidth: 0,

      marginLeft:
        spacing.md,
    },

    profileSummaryName: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 14,
      lineHeight: 18,
    },

    profileSummaryRole: {
      marginTop: 2,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 14,
    },

    activeBadge: {
      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.xs,

      paddingHorizontal:
        spacing.sm,

      paddingVertical: 5,

      borderRadius:
        radius.pill,

      backgroundColor:
        colors.glassSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    activeDot: {
      width: 6,
      height: 6,

      borderRadius: 3,

      backgroundColor:
        colors.success,
    },

    activeText: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 9,
      lineHeight: 12,
    },

    section: {
      marginTop:
        spacing.xxxl,
    },

    sectionEyebrow: {
      color:
        colors.link,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 14,

      letterSpacing: 1.4,
    },

    sectionTitle: {
      marginTop:
        spacing.sm,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 25,
      lineHeight: 31,
    },

    actionList: {
      marginTop:
        spacing.lg,

      gap: spacing.sm,
    },

    actionCard: {
      minHeight: 92,

      padding:
        spacing.md,

      borderRadius:
        radius.md,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    actionCardPressed: {
      opacity: 0.82,

      transform: [
        {
          scale: 0.99,
        },
      ],
    },

    actionCardDisabled: {
      opacity: 0.58,
    },

    actionIcon: {
      width: 46,
      height: 46,

      borderRadius:
        radius.md,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    actionContent: {
      flex: 1,
      minWidth: 0,
    },

    actionTitleRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.sm,
    },

    actionTitle: {
      flexShrink: 1,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 14,
      lineHeight: 18,
    },

    actionBadge: {
      paddingHorizontal: spacing.sm,
      paddingVertical: 4,
      borderRadius: radius.pill,
      backgroundColor: colors.plumSoft,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    actionBadgeText: {
      color: colors.link,
      fontFamily: fonts.sansSemiBold,
      fontSize: 8,
      lineHeight: 10,
      letterSpacing: 0.6,
    },

    actionDescription: {
      marginTop: 3,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 16,
    },

    tipCard: {
      marginTop:
        spacing.xxl,

      padding:
        spacing.lg,

      borderRadius:
        radius.md,

      flexDirection:
        "row",

      alignItems:
        "flex-start",

      gap: spacing.md,

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    tipSpark: {
      color:
        colors.link,

      fontFamily:
        fonts.display,

      fontSize: 20,
      lineHeight: 24,
    },

    tipContent: {
      flex: 1,
    },

    tipTitle: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    tipText: {
      marginTop:
        spacing.xs,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 17,
    },

    bottomSpace: {
      height: 120,
    },

    pressed: {
      opacity: 0.75,
    },
  }),
);