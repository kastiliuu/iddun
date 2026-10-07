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
  getMyJobApplications,
  type JobApplication,
} from "@/api/jobs";

import {
  EmptyState,
} from "@/components/EmptyState";

import {
  Icon,
} from "@/components/Icon";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function JobApplicationsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [items, setItems] =
    useState<JobApplication[]>(
      [],
    );
  const [loading, setLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);

  const load = useCallback(
    async () => {
      setLoading(true);

      try {
        const response =
          await getMyJobApplications();

        setItems(
          response.items,
        );
        setError(null);
      } catch (requestError) {
        setItems([]);
        setError(
          requestError
            instanceof Error
            ? requestError.message
            : "Não foi possível carregar suas candidaturas.",
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
            onPress={() =>
              router.back()
            }
            style={styles.headerButton}
          >
            <Icon
              name="arrow-left"
              size={19}
              color={colors.onSurface}
            />
          </Pressable>

          <Text style={styles.headerTitle}>
            Minhas candidaturas
          </Text>

          <View style={styles.headerPlaceholder} />
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>
            SUA JORNADA
          </Text>

          <Text style={styles.title}>
            Oportunidades que você escolheu.
          </Text>

          <Text style={styles.description}>
            Acompanhe as vagas em que seu perfil profissional foi enviado.
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
            title="Candidaturas indisponíveis"
            description={error}
            actionLabel="Tentar novamente"
            onActionPress={() => {
              void load();
            }}
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="Nenhuma candidatura ainda"
            description="Explore as vagas abertas e encontre uma oportunidade que combine com seu momento."
            actionLabel="Explorar vagas"
            onActionPress={() =>
              router.push(
                "/jobs",
              )
            }
          />
        ) : (
          <View style={styles.list}>
            {items.map(
              (application) => {
                const active =
                  application.status ===
                  "submitted";

                return (
                  <Pressable
                    key={application.id}
                    accessibilityRole="button"
                    accessibilityLabel={
                      `${application.job.title} em ${application.job.establishment.name}`
                    }
                    onPress={() =>
                      router.push(
                        `/job/${application.job.id}`,
                      )
                    }
                    style={({ pressed }) => [
                      styles.card,
                      pressed &&
                        styles.pressed,
                    ]}
                  >
                    <View style={styles.cardTop}>
                      <View style={styles.iconWrap}>
                        <Icon
                          name={
                            active
                              ? "send"
                              : "x-circle"
                          }
                          size={18}
                          color={
                            active
                              ? colors.plum
                              : colors.muted
                          }
                        />
                      </View>

                      <View style={styles.cardCopy}>
                        <Text style={styles.cardTitle}>
                          {application.job.title}
                        </Text>

                        <Text style={styles.cardBusiness}>
                          {application.job.establishment.name}
                        </Text>
                      </View>

                      <View
                        style={[
                          styles.statusPill,
                          !active &&
                            styles.statusPillMuted,
                        ]}
                      >
                        <Text
                          style={[
                            styles.statusText,
                            !active &&
                              styles.statusTextMuted,
                          ]}
                        >
                          {active
                            ? "Enviada"
                            : "Retirada"}
                        </Text>
                      </View>
                    </View>

                    <Text style={styles.meta}>
                      {[
                        application.job.city,
                        application.job.state,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </Text>
                  </Pressable>
                );
              },
            )}
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
      letterSpacing: 1.3,
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
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 13,
      lineHeight: 19,
    },

    loading: {
      minHeight: 260,
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

    cardTop: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
    },

    iconWrap: {
      width: 40,
      height: 40,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
    },

    cardCopy: {
      flex: 1,
      minWidth: 0,
    },

    cardTitle: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 14,
    },

    cardBusiness: {
      marginTop: 3,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 11,
    },

    statusPill: {
      paddingHorizontal: spacing.sm,
      paddingVertical: 5,
      borderRadius: radius.pill,
      backgroundColor: colors.plumSoft,
    },

    statusPillMuted: {
      backgroundColor: colors.glassSoft,
    },

    statusText: {
      color: colors.plum,
      fontFamily: fonts.sansMedium,
      fontSize: 10,
    },

    statusTextMuted: {
      color: colors.muted,
    },

    meta: {
      marginTop: spacing.md,
      color: colors.onSurfaceSecondary,
      fontFamily: fonts.sans,
      fontSize: 11,
    },

    pressed: {
      opacity: 0.8,
    },

    bottomSpace: {
      height: 80,
    },
  }),
);
