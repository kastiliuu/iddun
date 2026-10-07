import React, { useMemo, useState } from "react";
import {
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";

import { logout } from "@/api/auth";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Icon, IconName } from "@/components/Icon";
import { useToast } from "@/components/Toast";
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

type MenuItemProps = {
  icon: IconName;
  title: string;
  subtitle?: string;
  onPress?: () => void;
  danger?: boolean;
  disabled?: boolean;
};

function MenuItem({
  icon,
  title,
  subtitle,
  onPress,
  danger = false,
  disabled = false,
}: MenuItemProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={
        subtitle ? `${title}. ${subtitle}` : title
      }
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={() => {
        if (!onPress) return;

        Haptics.impactAsync(
          Haptics.ImpactFeedbackStyle.Light,
        ).catch(() => {});

        onPress();
      }}
      style={({ pressed }) => [
        styles.menuItem,
        disabled && styles.menuItemDisabled,
        pressed && !disabled && styles.pressed,
      ]}
    >
      <View
        style={[
          styles.menuIcon,
          danger && styles.menuIconDanger,
        ]}
      >
        <Icon
          name={icon}
          size={18}
          color={danger ? colors.error : colors.plum}
        />
      </View>

      <View style={styles.menuContent}>
        <Text
          style={[
            styles.menuTitle,
            danger && styles.menuTitleDanger,
          ]}
        >
          {title}
        </Text>

        {subtitle ? (
          <Text
            style={styles.menuSubtitle}
            numberOfLines={1}
          >
            {subtitle}
          </Text>
        ) : null}
      </View>

      {!danger ? (
        <Icon
          name={disabled ? "clock" : "chevron-right"}
          size={18}
          color={colors.muted}
        />
      ) : null}
    </Pressable>
  );
}

export default function ProfileScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const [loggingOut, setLoggingOut] = useState(false);

  const user = store.getUser();
  const graphState = store.graphState();
  const followingCount =
    store.following().length +
    graphState.follows.length;
  const favoriteCount =
    store.favorites("posts").length +
    store.favorites("professionals").length +
    store.favorites("services").length +
    graphState.saves.length;

  const roleLabel = useMemo(() => {
    if (!user) return null;

    switch (user.role) {
      case "professional":
        return "Profissional";
      case "establishment":
        return "Estabelecimento";
      case "client":
      default:
        return "Cliente";
    }
  }, [user]);

  const handleLogout = async () => {
    if (loggingOut) return;

    setLoggingOut(true);

    try {
      await logout();

      toast.show({
        title: "Sessão encerrada",
        body:
          "Você continua podendo explorar o IDDUN como visitante.",
        icon: "log-out",
      });
    } catch {
      toast.show({
        title: "Não foi possível sair",
        body:
          "Tente novamente para encerrar a sessão neste aparelho.",
        icon: "alert-circle",
      });
    } finally {
      setLoggingOut(false);
    }
  };

  const handleBecomeProfessional = () => {
    if (!user) {
      router.push({
        pathname: "/login",
        params: {
          mode: "signup",
          accountType: "professional",
        },
      });
      return;
    }

    router.push("/signup-pro");
  };

  if (!user) {
    return (
      <View style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.header}>
            <Image
              source={require(
                "../../../assets/branding/iddun-logo-white.png"
              )}
              style={styles.logo}
              contentFit="contain"
              accessibilityLabel="IDDUN"
            />

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Notificações"
              onPress={() => router.push("/notifications")}
              style={({ pressed }) => [
                styles.headerButton,
                pressed && styles.pressed,
              ]}
            >
              <Icon
                name="bell"
                size={20}
                color={colors.onSurface}
              />
            </Pressable>
          </View>

          <View style={styles.guestHero}>
            <View style={styles.guestIcon}>
              <Icon
                name="user"
                size={28}
                color={colors.plum}
              />
            </View>

            <Text style={styles.eyebrow}>
              SEU ESPAÇO
            </Text>

            <Text style={styles.guestTitle}>
              Seu IDDUN começa aqui.
            </Text>

            <Text style={styles.guestDescription}>
              Entre para salvar favoritos, seguir
              profissionais, comentar e acompanhar seus
              agendamentos.
            </Text>

            <View style={styles.guestButtons}>
              <Button
                title="Entrar"
                onPress={() => router.push("/login")}
                fullWidth
              />

              <Button
                title="Criar conta"
                variant="secondary"
                onPress={() =>
                  router.push({
                    pathname: "/login",
                    params: {
                      mode: "signup",
                      accountType: "client",
                    },
                  })
                }
                fullWidth
              />
            </View>
          </View>

          <View style={styles.professionalInvite}>
            <Text
              accessible={false}
              style={styles.inviteSpark}
            >
              {SPARK}
            </Text>

            <Text style={styles.inviteTitle}>
              Trabalha com beleza?
            </Text>

            <Text style={styles.inviteDescription}>
              Crie uma presença profissional e transforme
              seu trabalho em descoberta.
            </Text>

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Conhecer IDDUN para profissionais"
              onPress={handleBecomeProfessional}
              style={({ pressed }) => [
                styles.inviteAction,
                pressed && styles.pressed,
              ]}
            >
              <Text style={styles.inviteActionText}>
                Conhecer
              </Text>

              <Icon
                name="arrow-right"
                size={15}
                color={colors.plum}
              />
            </Pressable>
          </View>

          <View style={styles.bottomSpace} />
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Image
            source={require(
              "../../../assets/branding/iddun-logo-white.png"
            )}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Dispositivos e sessões"
            onPress={() =>
              router.push("/sessions")
            }
            style={({ pressed }) => [
              styles.headerButton,
              pressed && styles.pressed,
            ]}
          >
            <Icon
              name="smartphone"
              size={19}
              color={colors.onSurface}
            />
          </Pressable>
        </View>

        <View style={styles.profileHeader}>
          <Avatar
            name={user.name}
            uri={user.avatar}
            size={82}
            ring="plum"
          />

          <Text style={styles.name}>
            {user.businessName ?? user.name}
          </Text>

          <View style={styles.roleBadge}>
            <Text
              accessible={false}
              style={styles.roleSpark}
            >
              {SPARK}
            </Text>

            <Text style={styles.roleText}>
              {roleLabel}
            </Text>
          </View>

          {user.specialty ? (
            <Text style={styles.specialty}>
              {user.specialty}
            </Text>
          ) : null}

          {user.city ? (
            <View style={styles.locationRow}>
              <Icon
                name="map-pin"
                size={13}
                color={colors.muted}
              />

              <Text style={styles.location}>
                {user.neighborhood
                  ? `${user.neighborhood} · ${user.city}`
                  : user.city}
              </Text>
            </View>
          ) : null}
        </View>

        <View style={styles.stats}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`${followingCount} perfis seguindo`}
            onPress={() =>
              router.push("/(tabs)/discover")
            }
            style={({ pressed }) => [
              styles.stat,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.statValue}>
              {followingCount}
            </Text>

            <Text style={styles.statLabel}>
              Seguindo
            </Text>
          </Pressable>

          <View style={styles.statDivider} />

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`${favoriteCount} favoritos`}
            onPress={() =>
              router.push("/(tabs)/favorites")
            }
            style={({ pressed }) => [
              styles.stat,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.statValue}>
              {favoriteCount}
            </Text>

            <Text style={styles.statLabel}>
              Favoritos
            </Text>
          </Pressable>
        </View>

        <View style={styles.menuSection}>
          <Text style={styles.sectionLabel}>
            CONTA
          </Text>

          <View style={styles.menuCard}>
            <MenuItem
              icon="user"
              title="Editar perfil"
              subtitle="Edição completa em preparação"
              disabled
            />

            <View style={styles.menuDivider} />

            <MenuItem
              icon="calendar"
              title="Meus agendamentos"
              subtitle="Próximos atendimentos e histórico"
              onPress={() =>
                router.push("/bookings")
              }
            />

            <View style={styles.menuDivider} />

            <MenuItem
              icon="bell"
              title="Notificações"
              subtitle="Horários, interações e novidades"
              onPress={() =>
                router.push("/notifications")
              }
            />

            <View style={styles.menuDivider} />

            <MenuItem
              icon="briefcase"
              title="Vagas"
              subtitle="Oportunidades na rede IDDUN"
              onPress={() =>
                router.push("/jobs")
              }
            />
          </View>
        </View>

        {user.role === "client" ? (
          <View style={styles.professionalSection}>
            <Text style={styles.sectionLabel}>
              PROFISSIONAL
            </Text>

            <View style={styles.upgradeCard}>
              <View style={styles.upgradeIcon}>
                <Icon
                  name="briefcase"
                  size={21}
                  color={colors.plum}
                />
              </View>

              <Text style={styles.upgradeTitle}>
                Leve seu trabalho para o IDDUN
              </Text>

              <Text style={styles.upgradeDescription}>
                Crie um perfil profissional ou de
                estabelecimento e comece a publicar seus
                trabalhos.
              </Text>

              <Button
                title="Tornar-me profissional"
                variant="secondary"
                onPress={handleBecomeProfessional}
                fullWidth
              />
            </View>
          </View>
        ) : (
          <View style={styles.menuSection}>
            <Text style={styles.sectionLabel}>
              MEU NEGÓCIO
            </Text>

            <View style={styles.menuCard}>
              <MenuItem
                icon="grid"
                title="Painel profissional"
                subtitle="Publicações, serviços e presença"
                onPress={() =>
                  router.push("/(tabs)/create")
                }
              />

              {user.role === "professional" ? (
                <>
                  <View style={styles.menuDivider} />

                  <MenuItem
                    icon="briefcase"
                    title="Minha presença profissional"
                    subtitle="Progresso, experiência e publicação"
                    onPress={() =>
                      router.push("/professional-onboarding")
                    }
                  />

                  <View style={styles.menuDivider} />

                  <MenuItem
                    icon="send"
                    title="Minhas candidaturas"
                    subtitle="Acompanhe vagas em que você demonstrou interesse"
                    onPress={() =>
                      router.push("/job-applications")
                    }
                  />
                </>
              ) : null}

              <View style={styles.menuDivider} />

              <MenuItem
                icon="star"
                title="Avaliações"
                subtitle="Painel de reputação em preparação"
                disabled
              />

              {user.role === "establishment" ? (
                <>
                  <View style={styles.menuDivider} />

                  <MenuItem
                    icon="users"
                    title="Equipe"
                    subtitle="Profissionais vinculados ao estabelecimento"
                    disabled={!user.profileId}
                    onPress={() => {
                      if (!user.profileId) {
                        return;
                      }

                      router.push(
                        `/establishment-team/${user.profileId}`,
                      );
                    }}
                  />

                  <View style={styles.menuDivider} />

                  <MenuItem
                    icon="briefcase"
                    title="Gerenciar vagas"
                    subtitle="Publique oportunidades e acompanhe candidatos"
                    disabled={!user.profileId}
                    onPress={() => {
                      if (!user.profileId) {
                        return;
                      }

                      router.push(
                        `/manage-jobs/${user.profileId}`,
                      );
                    }}
                  />
                </>
              ) : null}
            </View>
          </View>
        )}

        <View style={styles.menuSection}>
          <Text style={styles.sectionLabel}>
            IDDUN
          </Text>

          <View style={styles.menuCard}>
            <MenuItem
              icon="help-circle"
              title="Ajuda"
              subtitle="Central de ajuda em preparação"
              disabled
            />

            <View style={styles.menuDivider} />

            <MenuItem
              icon="smartphone"
              title="Dispositivos e sessões"
              subtitle="Revise onde sua conta está conectada"
              onPress={() =>
                router.push("/sessions")
              }
            />

            <View style={styles.menuDivider} />

            <MenuItem
              icon="shield"
              title="Privacidade"
              subtitle="Controle seus dados e preferências"
              onPress={() =>
                router.push("/privacy")
              }
            />

            <View style={styles.menuDivider} />

            <MenuItem
              icon="log-out"
              title={loggingOut ? "Saindo..." : "Sair"}
              danger
              disabled={loggingOut}
              onPress={handleLogout}
            />
          </View>
        </View>

        <View style={styles.footer}>
          <Image
            source={require(
              "../../../assets/branding/iddun-logo-white.png"
            )}
            style={styles.footerLogo}
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

          <Text style={styles.footerText}>
            Descoberta, conexão e experiência.
          </Text>
        </View>

        <View style={styles.bottomSpace} />
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  content: {
    paddingTop: 54,
    paddingHorizontal: spacing.lg,
  },
  header: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  logo: {
    width: 112,
    height: 34,
  },
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
  guestHero: {
    marginTop: spacing.xxxl,
    alignItems: "center",
    paddingHorizontal: spacing.md,
  },
  guestIcon: {
    width: 68,
    height: 68,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.plumSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  eyebrow: {
    marginTop: spacing.xl,
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 1.5,
  },
  guestTitle: {
    maxWidth: 320,
    marginTop: spacing.sm,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 32,
    lineHeight: 38,
    textAlign: "center",
    letterSpacing: -0.4,
  },
  guestDescription: {
    maxWidth: 330,
    marginTop: spacing.md,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 13,
    lineHeight: 20,
    textAlign: "center",
  },
  guestButtons: {
    width: "100%",
    marginTop: spacing.xl,
    gap: spacing.sm,
  },
  professionalInvite: {
    marginTop: spacing.xxxl,
    padding: spacing.xl,
    borderRadius: radius.lg,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  inviteSpark: {
    color: colors.plum,
    fontFamily: fonts.display,
    fontSize: 22,
    lineHeight: 26,
  },
  inviteTitle: {
    marginTop: spacing.md,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 22,
    lineHeight: 28,
  },
  inviteDescription: {
    marginTop: spacing.sm,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 12,
    lineHeight: 18,
  },
  inviteAction: {
    minHeight: touch.minimum,
    marginTop: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  inviteActionText: {
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
  },
  profileHeader: {
    marginTop: spacing.xl,
    alignItems: "center",
  },
  name: {
    marginTop: spacing.lg,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 27,
    lineHeight: 33,
    textAlign: "center",
  },
  roleBadge: {
    marginTop: spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.plumSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  roleSpark: {
    color: colors.plum,
    fontFamily: fonts.display,
    fontSize: 10,
  },
  roleText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: 10,
    letterSpacing: 0.4,
  },
  specialty: {
    marginTop: spacing.sm,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 12,
  },
  locationRow: {
    marginTop: spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  location: {
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 11,
  },
  stats: {
    minHeight: 78,
    marginTop: spacing.xxl,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  stat: {
    flex: 1,
    minHeight: 76,
    alignItems: "center",
    justifyContent: "center",
  },
  statValue: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 21,
    lineHeight: 26,
  },
  statLabel: {
    marginTop: 2,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 10,
  },
  statDivider: {
    width: 1,
    height: 36,
    backgroundColor: colors.divider,
  },
  menuSection: {
    marginTop: spacing.xxxl,
  },
  professionalSection: {
    marginTop: spacing.xxxl,
  },
  sectionLabel: {
    marginBottom: spacing.sm,
    color: colors.muted,
    fontFamily: fonts.sansMedium,
    fontSize: 9,
    lineHeight: 12,
    letterSpacing: 1.4,
  },
  menuCard: {
    overflow: "hidden",
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  menuItem: {
    minHeight: 72,
    paddingHorizontal: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  menuItemDisabled: {
    opacity: 0.4,
  },
  menuIcon: {
    width: 38,
    height: 38,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.plumSoft,
  },
  menuIconDanger: {
    backgroundColor: "rgba(239,68,68,0.10)",
  },
  menuContent: {
    flex: 1,
    minWidth: 0,
  },
  menuTitle: {
    color: colors.onSurface,
    fontFamily: fonts.sansMedium,
    fontSize: 13,
    lineHeight: 17,
  },
  menuTitleDanger: {
    color: colors.error,
  },
  menuSubtitle: {
    marginTop: 2,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 10,
    lineHeight: 14,
  },
  menuDivider: {
    height: 1,
    marginLeft: 66,
    backgroundColor: colors.divider,
  },
  upgradeCard: {
    padding: spacing.lg,
    borderRadius: radius.md,
    gap: spacing.md,
    backgroundColor: colors.plumSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  upgradeIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surfaceSecondary,
  },
  upgradeTitle: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 21,
    lineHeight: 27,
  },
  upgradeDescription: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 12,
    lineHeight: 18,
  },
  footer: {
    marginTop: spacing.xxxl,
    alignItems: "center",
    paddingVertical: spacing.xl,
  },
  footerLogo: {
    width: 86,
    height: 28,
    opacity: 0.7,
  },
  footerText: {
    marginTop: spacing.sm,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 10,
    lineHeight: 14,
  },
  bottomSpace: {
    height: 120,
  },
  pressed: {
    opacity: 0.72,
  },
}));