import React, {
  useCallback,
  useState,
} from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  useFocusEffect,
  useLocalSearchParams,
  useRouter,
} from "expo-router";

import {
  getManagedEstablishmentTeam,
  inviteProfessionalToTeam,
  removeProfessionalFromTeam,
  type TeamMembership,
  type TeamResponse,
} from "@/api/team";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toast";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function EstablishmentTeamScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const params = useLocalSearchParams<{
    id?: string;
  }>();

  const establishmentId =
    typeof params.id === "string"
      ? params.id
      : "";

  const [team, setTeam] =
    useState<TeamResponse | null>(null);
  const [loading, setLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);
  const [email, setEmail] =
    useState("");
  const [roleName, setRoleName] =
    useState("");
  const [inviting, setInviting] =
    useState(false);
  const [removingId, setRemovingId] =
    useState<string | null>(null);

  const load = useCallback(
    async () => {
      if (!establishmentId) {
        setError(
          "Estabelecimento não informado.",
        );
        setLoading(false);
        return;
      }

      setLoading(true);

      try {
        const response =
          await getManagedEstablishmentTeam(
            establishmentId,
          );

        setTeam(response);
        setError(null);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível carregar a equipe.",
        );
      } finally {
        setLoading(false);
      }
    },
    [establishmentId],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const handleInvite = async () => {
    const normalizedEmail =
      email.trim().toLowerCase();

    if (!normalizedEmail) {
      toast.show({
        title: "Informe o e-mail",
        body: "Use o e-mail da conta profissional cadastrada no IDDUN.",
        icon: "mail",
      });
      return;
    }

    setInviting(true);

    try {
      const response =
        await inviteProfessionalToTeam(
          establishmentId,
          {
            email: normalizedEmail,
            roleName:
              roleName.trim() || undefined,
          },
        );

      setTeam((current) =>
        current
          ? {
              ...current,
              items: [
                response.membership,
                ...current.items.filter(
                  (item) =>
                    item.id !==
                    response.membership.id,
                ),
              ],
            }
          : current,
      );

      setEmail("");
      setRoleName("");

      toast.show({
        title: "Convite enviado",
        body: `${response.membership.professional.name} precisa aceitar o vínculo.`,
        icon: "send",
      });
    } catch (requestError) {
      toast.show({
        title: "Não foi possível convidar",
        body:
          requestError instanceof Error
            ? requestError.message
            : "Revise os dados e tente novamente.",
        icon: "alert-circle",
      });
    } finally {
      setInviting(false);
    }
  };

  const confirmRemove = (
    membership: TeamMembership,
  ) => {
    Alert.alert(
      "Remover da equipe?",
      `${membership.professional.name} deixará de aparecer como membro ativo deste estabelecimento.`,
      [
        {
          text: "Voltar",
          style: "cancel",
        },
        {
          text: "Remover",
          style: "destructive",
          onPress: () => {
            setRemovingId(
              membership.id,
            );

            removeProfessionalFromTeam(
              establishmentId,
              membership.id,
            )
              .then(() => {
                setTeam((current) =>
                  current
                    ? {
                        ...current,
                        items:
                          current.items.filter(
                            (item) =>
                              item.id !==
                              membership.id,
                          ),
                      }
                    : current,
                );

                toast.show({
                  title: "Vínculo removido",
                  body: `${membership.professional.name} não faz mais parte da equipe ativa.`,
                  icon: "user-minus",
                });
              })
              .catch((requestError: unknown) => {
                toast.show({
                  title: "Não foi possível remover",
                  body:
                    requestError instanceof Error
                      ? requestError.message
                      : "Tente novamente em instantes.",
                  icon: "alert-circle",
                });
              })
              .finally(() => {
                setRemovingId(null);
              });
          },
        },
      ],
    );
  };

  const activeItems =
    team?.items.filter(
      (item) => item.status === "active",
    ) ?? [];

  const pendingItems =
    team?.items.filter(
      (item) => item.status === "pending",
    ) ?? [];

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => router.back()}
            style={({ pressed }) => [
              styles.headerButton,
              pressed && styles.pressed,
            ]}
          >
            <Icon
              name="arrow-left"
              size={20}
              color={colors.onSurface}
            />
          </Pressable>

          <Text style={styles.headerTitle}>
            Equipe
          </Text>

          <View style={styles.headerPlaceholder} />
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>
            ESTABELECIMENTO
          </Text>

          <Text style={styles.title}>
            {team?.establishment.name ||
              "Gerencie sua equipe."}
          </Text>

          <Text style={styles.description}>
            Convide profissionais, acompanhe pendências e mantenha os vínculos atualizados.
          </Text>
        </View>

        {loading ? (
          <View style={styles.loading}>
            <ActivityIndicator
              color={colors.plum}
            />
          </View>
        ) : error ? (
          <EmptyState
            title="Equipe indisponível"
            description={error}
            actionLabel="Tentar novamente"
            onActionPress={() => {
              void load();
            }}
          />
        ) : team ? (
          <>
            <View style={styles.inviteCard}>
              <View style={styles.sectionHeading}>
                <View style={styles.sectionIcon}>
                  <Icon
                    name="user-plus"
                    size={18}
                    color={colors.plum}
                  />
                </View>

                <View style={styles.sectionHeadingCopy}>
                  <Text style={styles.sectionTitle}>
                    Convidar profissional
                  </Text>

                  <Text style={styles.sectionSubtitle}>
                    O vínculo só fica ativo depois do aceite.
                  </Text>
                </View>
              </View>

              <TextInput
                value={email}
                onChangeText={setEmail}
                placeholder="E-mail profissional"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                style={styles.input}
                accessibilityLabel="E-mail do profissional"
              />

              <TextInput
                value={roleName}
                onChangeText={setRoleName}
                placeholder="Função no local (opcional)"
                placeholderTextColor={colors.muted}
                style={styles.input}
                accessibilityLabel="Função do profissional"
              />

              <Button
                title="Enviar convite"
                loading={inviting}
                onPress={() => {
                  void handleInvite();
                }}
                fullWidth
              />
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                EQUIPE ATIVA · {activeItems.length}
              </Text>

              {activeItems.length === 0 ? (
                <EmptyState
                  title="Nenhum profissional ativo"
                  description="Convide alguém para começar a montar a equipe deste estabelecimento."
                  compact
                />
              ) : (
                <View style={styles.list}>
                  {activeItems.map(
                    (membership) => (
                      <View
                        key={membership.id}
                        style={styles.memberCard}
                      >
                        <View style={styles.memberIcon}>
                          <Icon
                            name="user"
                            size={17}
                            color={colors.plum}
                          />
                        </View>

                        <View style={styles.memberCopy}>
                          <Text style={styles.memberName}>
                            {membership.professional.name}
                          </Text>

                          <Text style={styles.memberMeta}>
                            {membership.roleName ||
                              membership.professional.specialty ||
                              "Profissional"}
                          </Text>
                        </View>

                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Remover ${membership.professional.name} da equipe`}
                          disabled={
                            removingId === membership.id
                          }
                          onPress={() =>
                            confirmRemove(membership)
                          }
                          style={({ pressed }) => [
                            styles.removeButton,
                            pressed && styles.pressed,
                          ]}
                        >
                          {removingId === membership.id ? (
                            <ActivityIndicator
                              size="small"
                              color={colors.error}
                            />
                          ) : (
                            <Icon
                              name="user-minus"
                              size={17}
                              color={colors.error}
                            />
                          )}
                        </Pressable>
                      </View>
                    ),
                  )}
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                CONVITES PENDENTES · {pendingItems.length}
              </Text>

              {pendingItems.length === 0 ? (
                <Text style={styles.pendingEmpty}>
                  Nenhum convite aguardando resposta.
                </Text>
              ) : (
                <View style={styles.list}>
                  {pendingItems.map(
                    (membership) => (
                      <View
                        key={membership.id}
                        style={styles.memberCard}
                      >
                        <View style={styles.memberIcon}>
                          <Icon
                            name="clock"
                            size={17}
                            color={colors.plum}
                          />
                        </View>

                        <View style={styles.memberCopy}>
                          <Text style={styles.memberName}>
                            {membership.professional.name}
                          </Text>

                          <Text style={styles.memberMeta}>
                            {membership.roleName ||
                              "Aguardando aceite"}
                          </Text>
                        </View>

                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Cancelar convite de ${membership.professional.name}`}
                          disabled={
                            removingId === membership.id
                          }
                          onPress={() =>
                            confirmRemove(membership)
                          }
                          style={({ pressed }) => [
                            styles.removeButton,
                            pressed && styles.pressed,
                          ]}
                        >
                          <Icon
                            name="x"
                            size={18}
                            color={colors.error}
                          />
                        </Pressable>
                      </View>
                    ),
                  )}
                </View>
              )}
            </View>
          </>
        ) : null}

        <View style={styles.bottomSpace} />
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles(
  (colors) => ({
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

    headerTitle: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 14,
    },

    headerPlaceholder: {
      width: touch.minimum,
    },

    hero: {
      marginTop: spacing.xl,
    },

    eyebrow: {
      color: colors.plum,
      fontFamily: fonts.sansMedium,
      fontSize: 10,
      letterSpacing: 1.4,
    },

    title: {
      marginTop: spacing.sm,
      color: colors.onSurface,
      fontFamily: fonts.display,
      fontSize: 30,
      lineHeight: 36,
    },

    description: {
      marginTop: spacing.md,
      maxWidth: 360,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 13,
      lineHeight: 19,
    },

    loading: {
      minHeight: 220,
      alignItems: "center",
      justifyContent: "center",
    },

    inviteCard: {
      marginTop: spacing.xl,
      padding: spacing.lg,
      borderRadius: radius.lg,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
      gap: spacing.sm,
    },

    sectionHeading: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
      marginBottom: spacing.sm,
    },

    sectionIcon: {
      width: 42,
      height: 42,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    sectionHeadingCopy: {
      flex: 1,
    },

    sectionTitle: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 14,
    },

    sectionSubtitle: {
      marginTop: 2,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 11,
      lineHeight: 15,
    },

    input: {
      minHeight: 50,
      paddingHorizontal: spacing.md,
      borderRadius: radius.md,
      color: colors.onSurface,
      fontFamily: fonts.sans,
      fontSize: 13,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    section: {
      marginTop: spacing.xxl,
    },

    sectionLabel: {
      color: colors.muted,
      fontFamily: fonts.sansMedium,
      fontSize: 10,
      letterSpacing: 1.2,
    },

    list: {
      marginTop: spacing.md,
      gap: spacing.sm,
    },

    memberCard: {
      minHeight: 72,
      padding: spacing.md,
      borderRadius: radius.md,
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    memberIcon: {
      width: 38,
      height: 38,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
    },

    memberCopy: {
      flex: 1,
      minWidth: 0,
    },

    memberName: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 13,
    },

    memberMeta: {
      marginTop: 2,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 11,
    },

    removeButton: {
      width: touch.minimum,
      height: touch.minimum,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: radius.pill,
      backgroundColor: colors.glassSoft,
    },

    pendingEmpty: {
      marginTop: spacing.md,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 12,
      lineHeight: 17,
    },

    bottomSpace: {
      height: 80,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);
