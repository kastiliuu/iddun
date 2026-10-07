import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import {
  useFocusEffect,
  useLocalSearchParams,
  useRouter,
} from "expo-router";

import {
  getJobApplications,
  type JobApplication,
  type JobPost,
} from "@/api/jobs";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function JobCandidatesScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const params =
    useLocalSearchParams<{
      establishmentId?: string;
      jobId?: string;
    }>();

  const establishmentId = String(
    params.establishmentId ?? "",
  );
  const jobId = String(
    params.jobId ?? "",
  );

  const [job, setJob] =
    useState<JobPost | null>(null);
  const [items, setItems] =
    useState<JobApplication[]>([]);
  const [loading, setLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const response =
        await getJobApplications(
          establishmentId,
          jobId,
        );

      setJob(response.job);
      setItems(response.items);
      setError(null);
    } catch (requestError) {
      setItems([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os candidatos.",
      );
    } finally {
      setLoading(false);
    }
  }, [establishmentId, jobId]);

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
            onPress={() => router.back()}
            style={styles.headerButton}
          >
            <Icon
              name="arrow-left"
              size={19}
              color={colors.onSurface}
            />
          </Pressable>

          <Text style={styles.headerTitle}>
            Candidatos
          </Text>

          <View style={styles.headerPlaceholder} />
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>
            TALENTOS
          </Text>

          <Text style={styles.title}>
            {job?.title ?? "Candidaturas"}
          </Text>

          <Text style={styles.description}>
            Perfis profissionais que demonstraram interesse nesta vaga.
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
            title="Candidatos indisponíveis"
            description={error}
            actionLabel="Tentar novamente"
            onActionPress={() => {
              void load();
            }}
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="Nenhuma candidatura"
            description="Quando profissionais se candidatarem, eles aparecerão aqui."
          />
        ) : (
          <View style={styles.list}>
            {items.map((application) => {
              const professional =
                application.professional;

              if (!professional) {
                return null;
              }

              return (
                <Pressable
                  key={application.id}
                  accessibilityRole="button"
                  accessibilityLabel={
                    `Ver perfil de ${professional.name}`
                  }
                  onPress={() =>
                    router.push(
                      `/professional/${professional.routeId}`,
                    )
                  }
                  style={({ pressed }) => [
                    styles.card,
                    pressed &&
                      styles.pressed,
                  ]}
                >
                  <View style={styles.iconWrap}>
                    <Icon
                      name="user"
                      size={18}
                      color={colors.plum}
                    />
                  </View>

                  <View style={styles.copy}>
                    <Text style={styles.name}>
                      {professional.name}
                    </Text>

                    <Text style={styles.meta}>
                      {professional.specialty ||
                        "Profissional"}
                      {professional.city
                        ? ` · ${professional.city}`
                        : ""}
                    </Text>

                    {application.message ? (
                      <Text style={styles.message}>
                        {application.message}
                      </Text>
                    ) : null}
                  </View>

                  <Icon
                    name="chevron-right"
                    size={18}
                    color={colors.muted}
                  />
                </Pressable>
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
      minHeight: 240,
      alignItems: "center",
      justifyContent: "center",
    },
    list: {
      marginTop: spacing.xl,
      gap: spacing.md,
    },
    card: {
      padding: spacing.lg,
      flexDirection: "row",
      alignItems: "flex-start",
      gap: spacing.md,
      borderRadius: radius.lg,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },
    iconWrap: {
      width: 40,
      height: 40,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
    },
    copy: {
      flex: 1,
      minWidth: 0,
    },
    name: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 14,
    },
    meta: {
      marginTop: 3,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 11,
    },
    message: {
      marginTop: spacing.sm,
      color: colors.onSurfaceSecondary,
      fontFamily: fonts.sans,
      fontSize: 12,
      lineHeight: 17,
    },
    pressed: {
      opacity: 0.8,
    },
    bottomSpace: {
      height: 80,
    },
  }),
);
