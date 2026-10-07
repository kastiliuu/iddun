import React, {
  useCallback,
  useState,
} from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import {
  useFocusEffect,
  useRouter,
} from "expo-router";

import {
  acceptTeamInvitation,
  getTeamInvitations,
  rejectTeamInvitation,
  type TeamMembership,
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

export default function TeamInvitationsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const [items, setItems] =
    useState<TeamMembership[]>([]);
  const [loading, setLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);
  const [actingId, setActingId] =
    useState<string | null>(null);

  const load = useCallback(
    async () => {
      setLoading(true);

      try {
        const response =
          await getTeamInvitations();

        setItems(response.items);
        setError(null);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível carregar seus convites.",
        );
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const handleAccept = async (
    membership: TeamMembership,
  ) => {
    setActingId(membership.id);

    try {
      await acceptTeamInvitation(
        membership.id,
      );

      setItems((current) =>
        current.filter(
          (item) =>
            item.id !== membership.id,
        ),
      );

      toast.show({
        title: "Convite aceito",
        body: `Agora você faz parte de ${membership.establishment.name}.`,
        icon: "check-circle",
      });
    } catch (requestError) {
      toast.show({
        title: "Não foi possível aceitar",
        body:
          requestError instanceof Error
            ? requestError.message
            : "Tente novamente em instantes.",
        icon: "alert-circle",
      });
    } finally {
      setActingId(null);
    }
  };

  const handleReject = async (
    membership: TeamMembership,
  ) => {
    setActingId(membership.id);

    try {
      await rejectTeamInvitation(
        membership.id,
      );

      setItems((current) =>
        current.filter(
          (item) =>
            item.id !== membership.id,
        ),
      );

      toast.show({
        title: "Convite recusado",
        body: `O convite de ${membership.establishment.name} foi recusado.`,
        icon: "x-circle",
      });
    } catch (requestError) {
      toast.show({
        title: "Não foi possível recusar",
        body:
          requestError instanceof Error
            ? requestError.message
            : "Tente novamente em instantes.",
        icon: "alert-circle",
      });
    } finally {
      setActingId(null);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
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
            Convites
          </Text>

          <View style={styles.headerPlaceholder} />
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>
            EQUIPE PROFISSIONAL
          </Text>

          <Text style={styles.title}>
            Seus vínculos com estabelecimentos.
          </Text>

          <Text style={styles.description}>
            Aceite apenas convites de locais onde você realmente trabalha ou pretende atuar.
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
            title="Convites indisponíveis"
            description={error}
            actionLabel="Tentar novamente"
            onActionPress={() => {
              void load();
            }}
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="Nenhum convite pendente"
            description="Quando um estabelecimento convidar você para a equipe, o convite aparecerá aqui."
          />
        ) : (
          <View style={styles.list}>
            {items.map((membership) => {
              const busy =
                actingId === membership.id;
              const location = [
                membership.establishment.city,
                membership.establishment.state,
              ]
                .filter(Boolean)
                .join(" · ");

              return (
                <View
                  key={membership.id}
                  style={styles.card}
                >
                  <View style={styles.cardIcon}>
                    <Icon
                      name="briefcase"
                      size={19}
                      color={colors.plum}
                    />
                  </View>

                  <Text style={styles.cardTitle}>
                    {membership.establishment.name}
                  </Text>

                  <Text style={styles.cardMeta}>
                    {membership.roleName ||
                      "Profissional"}
                    {location
                      ? ` · ${location}`
                      : ""}
                  </Text>

                  <View style={styles.actions}>
                    <Button
                      title="Aceitar"
                      loading={busy}
                      disabled={busy}
                      onPress={() => {
                        void handleAccept(
                          membership,
                        );
                      }}
                      fullWidth
                    />

                    <Button
                      title="Recusar"
                      variant="secondary"
                      disabled={busy}
                      onPress={() => {
                        void handleReject(
                          membership,
                        );
                      }}
                      fullWidth
                    />
                  </View>
                </View>
              );
            })}
          </View>
        )}

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
      maxWidth: 360,
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

    list: {
      marginTop: spacing.xl,
      gap: spacing.md,
    },

    card: {
      padding: spacing.lg,
      borderRadius: radius.lg,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    cardIcon: {
      width: 42,
      height: 42,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    cardTitle: {
      marginTop: spacing.md,
      color: colors.onSurface,
      fontFamily: fonts.display,
      fontSize: 21,
      lineHeight: 27,
    },

    cardMeta: {
      marginTop: spacing.xs,
      color: colors.onSurfaceSecondary,
      fontFamily: fonts.sans,
      fontSize: 12,
      lineHeight: 17,
    },

    actions: {
      marginTop: spacing.lg,
      gap: spacing.sm,
    },

    bottomSpace: {
      height: 80,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);
