import React, { useCallback, useRef, useState } from "react";
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
  updateJob,
  getManagedJobs,
  publishJob,
  type JobPost,
  type ManagedJobsResponse,
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

const JOB_STATUS_LABELS: Record<string, string> = {
  draft: "Rascunho",
  published: "Publicada",
  closed: "Encerrada",
};

export default function ManageJobsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const params =
    useLocalSearchParams<{ id?: string }>();
  const establishmentId =
    Array.isArray(params.id) ? params.id[0] ?? "" : params.id ?? "";

  const [items, setItems] =
    useState<JobPost[]>([]);
  const [recruitment, setRecruitment] =
    useState<ManagedJobsResponse["recruitment"] | null>(null);
  const [loading, setLoading] =
    useState(true);
  const [saving, setSaving] =
    useState(false);
  const savingInFlight = useRef(false);
  const scrollRef = useRef<React.ComponentRef<typeof ScrollView>>(null);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [mutatingJobId, setMutatingJobId] = useState<string | null>(null);
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
      setRecruitment(response.recruitment ?? null);
      setError(null);
    } catch (requestError) {
      setItems([]);
      setRecruitment(null);
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

  const clearEditor = () => {
    setEditingJobId(null);
    setTitle("");
    setSpecialty("");
    setDescription("");
    setEmploymentType("");
    setCompensationText("");
  };

  const startEditing = (job: JobPost) => {
    if (savingInFlight.current || mutatingJobId || job.status === "closed") return;
    setEditingJobId(job.id);
    setTitle(job.title);
    setSpecialty(job.specialty ?? "");
    setDescription(job.description ?? "");
    setEmploymentType(job.employmentType ?? "");
    setCompensationText(job.compensationText ?? "");
    scrollRef.current?.scrollTo({ y: 160, animated: true });
  };

  const handleSave = async () => {
    if (savingInFlight.current || mutatingJobId) return;
    if (!editingJobId && !recruitment?.canCreate) return;
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

    savingInFlight.current = true;
    setSaving(true);

    try {
      const payload = {
        title: title.trim(),
        specialty: specialty.trim(),
        description: description.trim(),
        employmentType: employmentType.trim(),
        compensationText: compensationText.trim(),
      };
      if (editingJobId) {
        await updateJob(establishmentId, editingJobId, payload);
      } else {
        await createJob(establishmentId, payload);
      }
      toast.show({
        title: editingJobId ? "Vaga atualizada" : "Rascunho criado",
        body: editingJobId
          ? "Suas alterações foram salvas."
          : "Revise a vaga e publique quando estiver pronta.",
        icon: "check-circle",
      });
      clearEditor();
      await load();
    } catch (requestError) {
      toast.show({
        title: editingJobId
          ? "Não foi possível atualizar a vaga"
          : "Não foi possível criar a vaga",
        body: requestError instanceof Error
          ? requestError.message
          : "Tente novamente.",
        icon: "alert-circle",
      });
    } finally {
      savingInFlight.current = false;
      setSaving(false);
    }
  };

  const handlePublish = async (
    job: JobPost,
  ) => {
    if (mutatingJobId) return;
    setMutatingJobId(job.id);
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
    } finally {
      setMutatingJobId(null);
    }
  };

  const handleClose = async (
    job: JobPost,
  ) => {
    if (mutatingJobId) return;
    setMutatingJobId(job.id);
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
    } finally {
      setMutatingJobId(null);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView
        ref={scrollRef}
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

        {recruitment && !recruitment.canCreate ? (
          <View style={styles.formCard} accessibilityRole="summary">
            <Text style={styles.sectionTitle}>
              Recrutamento ainda não habilitado
            </Text>
            <Text style={styles.jobMeta}>
              Novas vagas dependem da habilitação feita pela equipe do IDDUN. Vagas existentes continuam editáveis e podem ser encerradas.
            </Text>
          </View>
        ) : null}

        {recruitment?.canCreate || editingJobId !== null ? (
        <View style={styles.formCard}>
          <Text style={styles.sectionTitle}>
            {editingJobId ? "Editar vaga" : "Nova vaga"}
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
            title={editingJobId ? "Salvar alterações" : "Criar rascunho"}
            loading={saving}
            disabled={saving || mutatingJobId !== null}
            onPress={() => {
              void handleSave();
            }}
            fullWidth
          />
          {editingJobId ? (
            <Button
              title="Cancelar edição"
              variant="outline"
              disabled={saving || mutatingJobId !== null}
              onPress={clearEditor}
              fullWidth
            />
          ) : null}
        </View>
        ) : null}

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
              description={
                recruitment?.canCreate
                  ? "Crie o primeiro rascunho usando o formulário acima."
                  : "Quando o recrutamento for habilitado, suas vagas aparecem aqui."
              }
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
                        · {JOB_STATUS_LABELS[job.status] ?? job.status}
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
                    {job.status !== "closed" ? (
                      <Button
                        title="Editar"
                        variant="outline"
                        compact
                        disabled={saving || mutatingJobId !== null}
                        onPress={() => startEditing(job)}
                      />
                    ) : null}
                    {job.status === "draft" &&
                    (job.publishedAt || recruitment?.canCreate) ? (
                      <Button
                        title="Publicar"
                        compact
                        loading={mutatingJobId === job.id}
                        disabled={mutatingJobId !== null || saving}
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
                          disabled={mutatingJobId !== null}
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
                          loading={mutatingJobId === job.id}
                          disabled={mutatingJobId !== null || saving}
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
      color: colors.link,
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
      color: colors.link,
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
