import React, {
  useCallback,
  useState,
} from "react";

import {
  ActivityIndicator,
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
  applyToJob,
  getJob,
  getMyJobApplications,
  withdrawJobApplication,
  type JobPost,
} from "@/api/jobs";

import {
  Button,
} from "@/components/Button";

import {
  EmptyState,
} from "@/components/EmptyState";

import {
  Icon,
} from "@/components/Icon";

import {
  useToast,
} from "@/components/Toast";

import {
  store,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function JobDetailScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const params =
    useLocalSearchParams<{
      id?: string;
    }>();

  const jobId = String(
    params.id ?? "",
  );

  const [job, setJob] =
    useState<JobPost | null>(
      null,
    );
  const [message, setMessage] =
    useState("");
  const [loading, setLoading] =
    useState(true);
  const [submitting, setSubmitting] =
    useState(false);
  const [applied, setApplied] =
    useState(false);
  const [error, setError] =
    useState<string | null>(null);

  const user = store.getUser();

  const load = useCallback(
    async () => {
      if (!jobId) {
        setError(
          "Vaga não encontrada.",
        );
        setLoading(false);
        return;
      }

      setLoading(true);

      try {
        const response =
          await getJob(
            jobId,
          );

        setJob(
          response.job,
        );

        if (
          user?.role ===
          "professional"
        ) {
          try {
            const mine =
              await getMyJobApplications();

            setApplied(
              mine.items.some(
                (item) =>
                  item.job.id ===
                    jobId &&
                  item.status ===
                    "submitted",
              ),
            );
          } catch {
            setApplied(false);
          }
        }

        setError(null);
      } catch (requestError) {
        setJob(null);
        setError(
          requestError
            instanceof Error
            ? requestError.message
            : "Não foi possível carregar a vaga.",
        );
      } finally {
        setLoading(false);
      }
    },
    [
      jobId,
      user?.role,
    ],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const handleApply =
    async () => {
      if (!user) {
        router.push(
          "/login",
        );
        return;
      }

      if (
        user.role !==
        "professional"
      ) {
        toast.show({
          title:
            "Perfil profissional necessário",
          body:
            "Use uma conta profissional para se candidatar.",
          icon:
            "briefcase",
        });
        return;
      }

      setSubmitting(true);

      try {
        await applyToJob(
          jobId,
          message.trim()
            || undefined,
        );

        setApplied(true);

        toast.show({
          title:
            "Candidatura enviada",
          body:
            "O estabelecimento já pode visualizar seu perfil.",
          icon:
            "check-circle",
        });
      } catch (requestError) {
        toast.show({
          title:
            "Não foi possível se candidatar",
          body:
            requestError
              instanceof Error
              ? requestError.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setSubmitting(false);
      }
    };

  const handleWithdraw =
    async () => {
      setSubmitting(true);

      try {
        await withdrawJobApplication(
          jobId,
        );

        setApplied(false);

        toast.show({
          title:
            "Candidatura retirada",
          body:
            "Você pode se candidatar novamente enquanto a vaga estiver publicada.",
          icon:
            "check-circle",
        });
      } catch (requestError) {
        toast.show({
          title:
            "Não foi possível retirar",
          body:
            requestError
              instanceof Error
              ? requestError.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setSubmitting(false);
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
            onPress={() =>
              router.back()
            }
            style={styles.headerButton}
          >
            <Icon
              name="arrow-left"
              size={19}
              color={
                colors.onSurface
              }
            />
          </Pressable>

          <Text style={styles.headerTitle}>
            Detalhe da vaga
          </Text>

          <View style={styles.headerPlaceholder} />
        </View>

        {loading ? (
          <View style={styles.loading}>
            <ActivityIndicator
              color={
                colors.plum
              }
            />
          </View>
        ) : error || !job ? (
          <EmptyState
            title="Vaga indisponível"
            description={
              error
              ?? "Esta vaga não está mais disponível."
            }
            actionLabel="Voltar para vagas"
            onActionPress={() =>
              router.replace(
                "/jobs",
              )
            }
          />
        ) : (
          <>
            <View style={styles.hero}>
              <Text style={styles.eyebrow}>
                {job.specialty
                  ?? "OPORTUNIDADE"}
              </Text>

              <Text style={styles.title}>
                {job.title}
              </Text>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel={
                  `Ver ${job.establishment.name}`
                }
                onPress={() =>
                  router.push(
                    `/establishment/${job.establishment.routeId}`,
                  )
                }
                style={styles.businessRow}
              >
                <View style={styles.businessIcon}>
                  <Icon
                    name="home"
                    size={17}
                    color={colors.plum}
                  />
                </View>

                <View style={styles.businessCopy}>
                  <Text style={styles.businessName}>
                    {job.establishment.name}
                  </Text>

                  <Text style={styles.businessLocation}>
                    {[
                      job.neighborhood,
                      job.city,
                      job.state,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </Text>
                </View>

                <Icon
                  name="chevron-right"
                  size={18}
                  color={colors.muted}
                />
              </Pressable>
            </View>

            <View style={styles.metaGrid}>
              {job.employmentType ? (
                <View style={styles.metaCard}>
                  <Icon
                    name="briefcase"
                    size={16}
                    color={colors.plum}
                  />
                  <Text style={styles.metaLabel}>
                    Modelo
                  </Text>
                  <Text style={styles.metaValue}>
                    {job.employmentType}
                  </Text>
                </View>
              ) : null}

              {job.compensationText ? (
                <View style={styles.metaCard}>
                  <Icon
                    name="dollar-sign"
                    size={16}
                    color={colors.plum}
                  />
                  <Text style={styles.metaLabel}>
                    Remuneração
                  </Text>
                  <Text style={styles.metaValue}>
                    {job.compensationText}
                  </Text>
                </View>
              ) : null}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                SOBRE A VAGA
              </Text>

              <Text style={styles.description}>
                {job.description}
              </Text>
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                CANDIDATURA
              </Text>

              {user?.role === "professional" &&
              !applied ? (
                <TextInput
                  value={message}
                  onChangeText={setMessage}
                  placeholder="Escreva uma mensagem breve (opcional)"
                  placeholderTextColor={colors.muted}
                  multiline
                  maxLength={1200}
                  style={styles.messageInput}
                />
              ) : null}

              {applied ? (
                <View style={styles.appliedCard}>
                  <Icon
                    name="check-circle"
                    size={20}
                    color={colors.success}
                  />

                  <View style={styles.appliedCopy}>
                    <Text style={styles.appliedTitle}>
                      Candidatura enviada
                    </Text>

                    <Text style={styles.appliedText}>
                      Seu perfil profissional foi encaminhado ao estabelecimento.
                    </Text>
                  </View>
                </View>
              ) : null}

              <View style={styles.actionWrap}>
                <Button
                  title={
                    applied
                      ? "Retirar candidatura"
                      : user
                        ? "Quero me candidatar"
                        : "Entrar para me candidatar"
                  }
                  variant={
                    applied
                      ? "outline"
                      : "primary"
                  }
                  loading={submitting}
                  onPress={() => {
                    if (applied) {
                      void handleWithdraw();
                    } else {
                      void handleApply();
                    }
                  }}
                  fullWidth
                />
              </View>
            </View>
          </>
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
      alignItems: "center",
      justifyContent: "center",
      borderRadius: radius.pill,
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

    loading: {
      minHeight: 300,
      alignItems: "center",
      justifyContent: "center",
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
      fontSize: 32,
      lineHeight: 38,
    },

    businessRow: {
      marginTop: spacing.xl,
      padding: spacing.md,
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
      borderRadius: radius.md,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    businessIcon: {
      width: 40,
      height: 40,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
    },

    businessCopy: {
      flex: 1,
      minWidth: 0,
    },

    businessName: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 13,
    },

    businessLocation: {
      marginTop: 2,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 11,
    },

    metaGrid: {
      marginTop: spacing.lg,
      flexDirection: "row",
      gap: spacing.sm,
    },

    metaCard: {
      flex: 1,
      minHeight: 98,
      padding: spacing.md,
      borderRadius: radius.md,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    metaLabel: {
      marginTop: spacing.sm,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 10,
    },

    metaValue: {
      marginTop: 3,
      color: colors.onSurface,
      fontFamily: fonts.sansMedium,
      fontSize: 12,
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

    description: {
      marginTop: spacing.md,
      color: colors.onSurfaceSecondary,
      fontFamily: fonts.sans,
      fontSize: 14,
      lineHeight: 21,
    },

    messageInput: {
      marginTop: spacing.md,
      minHeight: 110,
      padding: spacing.md,
      textAlignVertical: "top",
      borderRadius: radius.md,
      color: colors.onSurface,
      fontFamily: fonts.sans,
      fontSize: 13,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    appliedCard: {
      marginTop: spacing.md,
      padding: spacing.md,
      flexDirection: "row",
      alignItems: "flex-start",
      gap: spacing.md,
      borderRadius: radius.md,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    appliedCopy: {
      flex: 1,
    },

    appliedTitle: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 13,
    },

    appliedText: {
      marginTop: 3,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 12,
      lineHeight: 17,
    },

    actionWrap: {
      marginTop: spacing.lg,
    },

    bottomSpace: {
      height: 80,
    },
  }),
);
