import React, { useCallback, useState } from "react";
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
  closeJob,
  createJob,
  getManagedJobs,
  publishJob,
  type JobPost,
} from "@/api/jobs";
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

export default function ManageJobsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const params =
    useLocalSearchParams<{ id?: string }>();
  const establishmentId = String(
    params.id ?? "",
  );

  const [items, setItems] =
    useState<JobPost[]>([]);
  const [loading, setLoading] =
    useState(true);
  const [saving, setSaving] =
    useState(false);
  const [title, setTitle] =
    useState("");
  const [specialty, setSpecialty] =
    useState("");
  const [description, setDescription] =
    useState("");
  const [employmentType, setEmploymentType] =
    useState("");
  const [compensationText, setCompensationText] =
    useState("");
  const [error, setError] =
    useState<string | null>(null);

  const load = useCallback(async () => {
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
        await getManagedJobs(
          establishmentId,
        );

      setItems(response.items);
      setError(null);
    } catch (requestError) {
      setItems([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar as vagas.",
      );
    } finally {
      setLoading(false);
    }
  }, [establishmentId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const handleCreate = async () => {
    if (
      !title.trim() ||
      !description.trim()
    ) {
      toast.show({
        title: "Complete a vaga",
        body:
          "Título e descrição são obrigatórios.",
        icon: "alert-circle",
      });
      return;
    }

    setSaving(true);

    try {
      await createJob(
        establishmentId,
        {
          title: title.trim(),
          specialty:
            specialty.trim() || undefined,
          description:
            description.trim(),
          employmentType:
            employmentType.trim() ||
            undefined,
          compensationText:
            compensationText.trim() ||
            undefined,
        },
      );

      setTitle("");
      setSpecialty("");
      setDescription("");
      setEmploymentType("");
      setCompensationText("");

      toast.show({
        title: "Rascunho criado",
        body:
          "Revise a vaga e publique quando estiver pronta.",
        icon: "check-circle",
      });

      await load();
    } catch (requestError) {
      toast.show({
        title:
          "Não foi possível criar a vaga",
        body:
          requestError instanceof Error
            ? requestError.message
            : "Tente novamente.",
        icon: "alert-circle",
      });
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async (
    job: JobPost,
  ) => {
    try {
      await publishJob(
        establishmentId,
        job.id,
      );
      toast.show({
        title: "Vaga publicada",
        icon: "check-circle",
      });
      await load();
    } catch (requestError) {
      toast.show({
        title:
          "Não foi possível publicar",
        body:
          requestError instanceof Error
            ? requestError.message
            : "Tente novamente.",
        icon: "alert-circle",
      });
    }
  };

  const handleClose = async (
    job: JobPost,
  ) => {
    try {
      await closeJob(
        establishmentId,
        job.id,
      );
      toast.show({
        title: "Vaga encerrada",
        icon: "check-circle",
      });
      await load();
    } catch (requestError) {
      toast.show({
        title:
          "Não foi possível encerrar",
        body:
          requestError instanceof Error
            ? requestError.message
            : "Tente novamente.",
        icon: "alert-circle",
      });
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
            style={styles.headerButton}
          >
            <Icon
              name="arrow-left"
              size={19}
              color={colors.onSurface}
            />
          </Pressable>

          <Text style={styles.headerTitle}>
            Gerenciar vagas
          </Text>

          <View style={styles.headerPlaceholder} />
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>
            CONTRATAÇÃO
          </Text>

          <Text style={styles.title}>
            Encontre novos talentos.
          </Text>

          <Text style={styles.description}>
            Publique vagas gratuitas e acompanhe as candidaturas recebidas.
          </Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.sectionTitle}>
            Nova vaga
          </Text>

          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="Título da vaga"
            placeholderTextColor={colors.muted}
            style={styles.input}
          />

          <TextInput
            value={specialty}
            onChangeText={setSpecialty}
            placeholder="Especialidade"
            placeholderTextColor={colors.muted}
            style={styles.input}
          />

          <TextInput
            value={employmentType}
            onChangeText={setEmploymentType}
            placeholder="Modelo (CLT, parceria, comissão...)"
            placeholderTextColor={colors.muted}
            style={styles.input}
          />

          <TextInput
            value={compensationText}
            onChangeText={setCompensationText}
            placeholder="Remuneração (opcional)"
            placeholderTextColor={colors.muted}
            style={styles.input}
          />

          <TextInput
            value={description}
            onChangeText={setDescription}
            placeholder="Descrição da vaga"
            placeholderTextColor={colors.muted}
            multiline
            style={styles.textarea}
          />

          <Button
            title="Criar rascunho"
            loading={saving}
            onPress={() => {
              void handleCreate();
            }}
            fullWidth
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>
            SUAS VAGAS
          </Text>

          {loading ? (
            <View style={styles.loading}>
              <ActivityIndicator
                color={colors.plum}
              />
            </View>
          ) : error ? (
            <EmptyState
              title="Vagas indisponíveis"
              description={error}
              actionLabel="Tentar novamente"
              onActionPress={() => {
                void load();
              }}
              compact
            />
          ) : items.length === 0 ? (
            <EmptyState
              title="Nenhuma vaga criada"
              description="Crie o primeiro rascunho usando o formulário acima."
              compact
            />
          ) : (
            <View style={styles.list}>
              {items.map((job) => (
                <View
                  key={job.id}
                  style={styles.jobCard}
                >
                  <View style={styles.jobTop}>
                    <View style={styles.jobCopy}>
                      <Text style={styles.jobTitle}>
                        {job.title}
                      </Text>

                      <Text style={styles.jobMeta}>
                        {job.specialty ||
                          "Sem especialidade"}{" "}
                        · {job.status}
                      </Text>
                    </View>

                    {typeof job.applicationsCount ===
                    "number" ? (
                      <Text style={styles.count}>
                        {job.applicationsCount}
                      </Text>
                    ) : null}
                  </View>

                  <View style={styles.actions}>
                    {job.status === "draft" ? (
                      <Button
                        title="Publicar"
                        compact
                        onPress={() => {
                          void handlePublish(job);
                        }}
                      />
                    ) : null}

                    {job.status ===
                    "published" ? (
                      <>
                        <Button
                          title="Candidatos"
                          variant="secondary"
                          compact
                          onPress={() =>
                            router.push(
                              `/job-candidates/${encodeURIComponent(establishmentId)}/${job.id}`,
                            )
                          }
                        />

                        <Button
                          title="Encerrar"
                          variant="outline"
                          compact
                          onPress={() => {
                            void handleClose(job);
                          }}
                        />
                      </>
                    ) : null}
                  </View>
                </View>
              ))}
            </View>
          )}
        </View>

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
    formCard: {
      marginTop: spacing.xl,
      padding: spacing.lg,
      gap: spacing.sm,
      borderRadius: radius.lg,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },
    sectionTitle: {
      marginBottom: spacing.sm,
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 15,
    },
    input: {
      minHeight: 48,
      paddingHorizontal: spacing.md,
      borderRadius: radius.md,
      color: colors.onSurface,
      fontFamily: fonts.sans,
      fontSize: 13,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },
    textarea: {
      minHeight: 110,
      padding: spacing.md,
      borderRadius: radius.md,
      textAlignVertical: "top",
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
    loading: {
      minHeight: 160,
      alignItems: "center",
      justifyContent: "center",
    },
    list: {
      marginTop: spacing.md,
      gap: spacing.md,
    },
    jobCard: {
      padding: spacing.lg,
      borderRadius: radius.lg,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },
    jobTop: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
    },
    jobCopy: {
      flex: 1,
      minWidth: 0,
    },
    jobTitle: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 14,
    },
    jobMeta: {
      marginTop: 3,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 11,
    },
    count: {
      minWidth: 28,
      textAlign: "center",
      color: colors.plum,
      fontFamily: fonts.sansSemiBold,
      fontSize: 13,
    },
    actions: {
      marginTop: spacing.md,
      flexDirection: "row",
      flexWrap: "wrap",
      gap: spacing.sm,
    },
    bottomSpace: {
      height: 80,
    },
  }),
);
