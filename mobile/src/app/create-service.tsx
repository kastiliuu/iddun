import React, { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Image, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useLocalSearchParams, usePreventRemove, useRouter } from "expo-router";

import { ApiError } from "@/api/client";
import {
  createProfessionalServiceDraft,
  getProfessionalServiceDetail,
  getProfessionalServiceEstablishments,
  updateProfessionalServiceDraft,
  uploadProfessionalServiceImage,
  type ServiceEstablishment,
} from "@/api/services";
import type { UploadableImage } from "@/api/media";
import { MediaPermissionError, pickAndPrepareImage } from "@/media/imagePipeline";
import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import {
  EMPTY,
  LIMITS,
  SERVICE_CATEGORIES,
  SERVICE_STEPS,
  buildPayload,
  categoryLabel,
  firstReachableStep,
  formatMoney,
  parseMoney,
  stepErrors,
  stepForServerError,
  type ServiceWizardValues,
  type StepErrors,
} from "@/services/serviceWizard";
import { makeStyles, radius, spacing, touch, typography, useTheme } from "@/theme";

/*
 * P-002 · Wizard A no app: as mesmas cinco etapas da Web, uma por vez.
 * Salvar cria (ou mantém) um rascunho; publicar é feito em Meus serviços.
 * Nada aqui abre horários. A foto escolhida só é enviada depois que o
 * rascunho é salvo (V1-CONV-D06), com as mesmas regras da Web.
 */

const EMPTY_VALUES: ServiceWizardValues = {
  name: "",
  category: "unhas",
  shortDescription: "",
  description: "",
  regularPrice: "",
  price: "",
  duration: "60",
  establishmentId: null,
};

const LAST = SERVICE_STEPS.length - 1;

export default function CreateServiceScreen() {
  const router = useRouter();
  const { editId } = useLocalSearchParams<{ editId?: string }>();
  const serviceId = editId && /^\d+$/.test(editId) ? Number(editId) : null;
  const { colors } = useTheme();
  const styles = useStyles();
  const [values, setValues] = useState<ServiceWizardValues>(EMPTY_VALUES);
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState<StepErrors>({});
  const [saving, setSaving] = useState(false);
  const [fetching, setFetching] = useState(Boolean(editId));
  const [editable, setEditable] = useState(!editId);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [establishments, setEstablishments] = useState<ServiceEstablishment[]>([]);
  const [pendingImage, setPendingImage] = useState<UploadableImage | null>(null);
  const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);

  const disablePrevention = usePreventRemove(dirty && !saving, ({ repeat }) => {
    Alert.alert("Descartar alterações?", "O que você preencheu ainda não foi salvo.", [
      { text: "Continuar editando", style: "cancel" },
      { text: "Descartar", style: "destructive", onPress: () => { setDirty(false); repeat(); } },
    ]);
  });

  useEffect(() => {
    let active = true;
    getProfessionalServiceEstablishments().then(({ items }) => {
      if (active) setEstablishments(items);
    }).catch(() => {
      if (active) setError("Não foi possível carregar os estabelecimentos vinculados.");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!editId) return;
    let active = true;
    if (!serviceId || serviceId <= 0) {
      Promise.resolve().then(() => {
        if (active) { setError("Serviço inválido."); setFetching(false); }
      });
      return () => { active = false; };
    }
    getProfessionalServiceDetail(serviceId).then(({ service }) => {
      if (!active) return;
      setValues({
        name: service.name,
        category: service.category,
        shortDescription: service.shortDescription,
        description: service.description ?? "",
        regularPrice: formatMoney(service.regularPrice).replace("R$ ", ""),
        price: formatMoney(service.price).replace("R$ ", ""),
        duration: String(service.durationMinutes),
        establishmentId: service.establishmentId,
      });
      setCurrentImageUrl(service.imageUrl ?? null);
      const canEdit = service.status === "draft" || service.status === "paused";
      setEditable(canEdit);
      if (!canEdit) setError("Somente rascunhos e serviços pausados podem ser editados.");
    }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar.");
    }).finally(() => {
      if (active) setFetching(false);
    });
    return () => { active = false; };
  }, [editId, serviceId]);

  const update = <K extends keyof ServiceWizardValues>(key: K, value: ServiceWizardValues[K]) => {
    setValues(current => ({ ...current, [key]: value }));
    setErrors(current => ({ ...current, [key]: undefined }));
    setDirty(true);
  };

  const goTo = (target: number) => {
    const reachable = target > step ? firstReachableStep(target, values) : target;
    setErrors(reachable < target ? stepErrors(reachable, values) : {});
    setStep(reachable);
  };

  const establishmentName = useMemo(() => {
    if (values.establishmentId === null) return "Atendimento independente";
    return establishments.find(item => item.id === values.establishmentId)?.name ?? "Estabelecimento vinculado";
  }, [establishments, values.establishmentId]);

  const chooseImage = async () => {
    try {
      const image = await pickAndPrepareImage("library", "cover");
      if (!image) return;
      setPendingImage(image);
      setDirty(true);
      setError(null);
    } catch (cause) {
      setError(cause instanceof MediaPermissionError || cause instanceof Error
        ? cause.message
        : "Não foi possível abrir a foto.");
    }
  };

  const submit = async () => {
    const payload = buildPayload(values);
    if (!payload) {
      goTo(LAST);
      return;
    }
    if (editId && (!serviceId || !editable)) return;
    setSaving(true);
    setError(null);
    try {
      let savedId = serviceId;
      if (serviceId) await updateProfessionalServiceDraft(serviceId, payload);
      else savedId = (await createProfessionalServiceDraft(payload)).service.id;
      setDirty(false);
      disablePrevention();
      if (pendingImage && savedId) {
        try {
          await uploadProfessionalServiceImage(savedId, pendingImage);
        } catch (cause) {
          Alert.alert(
            "Rascunho salvo, foto não enviada",
            `${cause instanceof Error ? cause.message : "Tente de novo."} Você pode enviar a foto em Editar serviço.`,
          );
        }
      }
      router.replace("/manage-services");
    } catch (cause) {
      const code = cause instanceof ApiError ? cause.code : undefined;
      const back = stepForServerError(code);
      if (back !== null) setStep(back);
      if (cause instanceof ApiError && cause.status === 401) {
        setError("Sua sessão terminou. Entre de novo para salvar; o que você preencheu continua aqui.");
      } else {
        setError(cause instanceof Error ? cause.message : "Não foi possível salvar o serviço.");
      }
    } finally {
      setSaving(false);
    }
  };

  const fieldError = (key: keyof ServiceWizardValues) => errors[key] ? (
    <Text accessibilityRole="alert" style={styles.fieldError}>{errors[key]}</Text>
  ) : null;

  const reviewRow = (label: string, value: string, target: number) => (
    <View key={label} style={styles.reviewRow}>
      <View style={styles.reviewCopy}>
        <Text style={styles.reviewLabel}>{label}</Text>
        <Text style={styles.reviewValue}>{value || EMPTY}</Text>
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel={`Editar ${label.toLowerCase()}`}
        onPress={() => setStep(target)} style={styles.reviewEdit}>
        <Text style={styles.reviewEditText}>Editar</Text>
      </Pressable>
    </View>
  );

  const money = (text: string) => {
    const value = parseMoney(text);
    return value === null || Number.isNaN(value) ? "" : formatMoney(value);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Pressable accessibilityRole="button" accessibilityLabel="Voltar"
        onPress={() => router.canGoBack() ? router.back() : router.replace("/manage-services")}
        style={styles.backButton}>
        <Icon name="arrow-left" size={20} color={colors.onSurface} />
      </Pressable>
      <Text style={styles.heading}>{editId ? "Editar serviço" : "Criar serviço"}</Text>
      <Text style={styles.description}>{editId ? "Atualize seu rascunho ou serviço pausado. O status não muda." : "Cinco etapas curtas. O rascunho fica privado até você publicar em Meus serviços."}</Text>

      <View accessibilityRole="progressbar" accessibilityLabel={`Etapa ${step + 1} de ${SERVICE_STEPS.length}: ${SERVICE_STEPS[step].label}`}
        accessibilityValue={{ min: 1, max: SERVICE_STEPS.length, now: step + 1 }} style={styles.progress}>
        {SERVICE_STEPS.map((item, index) => (
          <View key={item.key} style={[styles.progressDot, index < step && styles.progressDone, index === step && styles.progressCurrent]}>
            <Text style={[styles.progressNumber, index === step && styles.progressNumberCurrent]}>{index + 1}</Text>
          </View>
        ))}
      </View>

      <View style={styles.section}>
        <Text style={styles.stepCount}>Etapa {step + 1} de {SERVICE_STEPS.length}</Text>
        <Text accessibilityRole="header" style={styles.sectionTitle}>{SERVICE_STEPS[step].label}</Text>

        {step === 0 ? (
          <>
            <Text style={styles.label}>Nome do serviço</Text>
            <TextInput accessibilityLabel="Nome do serviço" value={values.name} onChangeText={text => update("name", text)}
              maxLength={LIMITS.title} placeholder="Ex.: Banho de gel" placeholderTextColor={colors.muted} style={styles.input} />
            {fieldError("name")}
            <Text style={styles.label}>Categoria</Text>
            <View style={styles.chips}>
              {SERVICE_CATEGORIES.map(([key, label]) => (
                <Pressable key={key} accessibilityRole="radio" accessibilityState={{ checked: values.category === key }}
                  onPress={() => update("category", key)} style={[styles.chip, values.category === key && styles.chipSelected]}>
                  <Text style={styles.chipText}>{label}</Text>
                </Pressable>
              ))}
            </View>
            {fieldError("category")}
            <Text style={styles.label}>Descrição resumida</Text>
            <TextInput accessibilityLabel="Descrição resumida" value={values.shortDescription}
              onChangeText={text => update("shortDescription", text)} maxLength={LIMITS.shortDescription} multiline
              placeholder="O que está incluído" placeholderTextColor={colors.muted} style={[styles.input, styles.multiline]} />
            <Text style={styles.help}>Aparece na lista de serviços. {values.shortDescription.length}/{LIMITS.shortDescription}</Text>
            {fieldError("shortDescription")}
            <Text style={styles.label}>Descrição completa (opcional)</Text>
            <TextInput accessibilityLabel="Descrição completa" value={values.description}
              onChangeText={text => update("description", text)} maxLength={LIMITS.description} multiline
              placeholder="Detalhes, cuidados e preparo" placeholderTextColor={colors.muted} style={[styles.input, styles.multiline]} />
            {fieldError("description")}
          </>
        ) : null}

        {step === 1 ? (
          <>
            <Text style={styles.help}>O preço IDDUN é o que o cliente vê para reservar. Ele não pode ser maior que o preço regular.</Text>
            <Text style={styles.label}>Preço regular (R$)</Text>
            <TextInput accessibilityLabel="Preço regular em reais" value={values.regularPrice} onChangeText={text => update("regularPrice", text)}
              keyboardType="decimal-pad" placeholder="120,00" placeholderTextColor={colors.muted} style={styles.input} />
            {fieldError("regularPrice")}
            <Text style={styles.label}>Preço IDDUN (R$)</Text>
            <TextInput accessibilityLabel="Preço IDDUN em reais" value={values.price} onChangeText={text => update("price", text)}
              keyboardType="decimal-pad" placeholder="100,00" placeholderTextColor={colors.muted} style={styles.input} />
            {fieldError("price")}
            <Text style={styles.label}>Duração em minutos</Text>
            <TextInput accessibilityLabel="Duração em minutos" value={values.duration} onChangeText={text => update("duration", text)}
              keyboardType="number-pad" placeholder="60" placeholderTextColor={colors.muted} style={styles.input} />
            <Text style={styles.help}>Entre {LIMITS.durationMin} e {LIMITS.durationMax} minutos.</Text>
            {fieldError("duration")}
          </>
        ) : null}

        {step === 2 ? (
          <>
            <Text style={styles.label}>Local do atendimento</Text>
            <View style={styles.chips}>
              <Pressable accessibilityRole="radio" accessibilityState={{ checked: values.establishmentId === null }}
                onPress={() => update("establishmentId", null)}
                style={[styles.chip, values.establishmentId === null && styles.chipSelected]}>
                <Text style={styles.chipText}>Independente</Text>
              </Pressable>
              {establishments.map((establishment) => (
                <Pressable key={establishment.id} accessibilityRole="radio"
                  accessibilityState={{ checked: values.establishmentId === establishment.id }}
                  onPress={() => update("establishmentId", establishment.id)}
                  style={[styles.chip, values.establishmentId === establishment.id && styles.chipSelected]}>
                  <Text style={styles.chipText}>{establishment.name}</Text>
                </Pressable>
              ))}
            </View>
            <Text style={styles.help}>Só aparecem estabelecimentos com vínculo ativo e aceito.</Text>
            <View style={styles.note}>
              <Icon name="calendar" size={20} color={colors.plum} />
              <Text style={styles.noteText}>Salvar não abre horários. Depois de publicar, em Meus serviços, você abre horários ou gera pela jornada semanal.</Text>
            </View>
          </>
        ) : null}

        {step === 3 ? (
          <>
            <Text style={styles.help}>Opcional. Uma foto real do seu trabalho ajuda o cliente a decidir. Sem foto, o serviço aparece com o nome da categoria em destaque, nunca com foto genérica.</Text>
            {pendingImage || currentImageUrl ? (
              <Image source={{ uri: pendingImage?.uri ?? currentImageUrl ?? undefined }}
                accessibilityLabel={pendingImage ? "Prévia da nova foto" : "Foto atual do serviço"}
                style={styles.imagePreview} resizeMode="cover" />
            ) : (
              <View style={styles.imageFallback} accessibilityLabel="Sem foto">
                <Text style={styles.imageFallbackText}>{categoryLabel(values.category)}</Text>
              </View>
            )}
            <Button title={pendingImage || currentImageUrl ? "Trocar foto" : "Escolher foto"} variant="outline" fullWidth
              disabled={saving} onPress={() => { void chooseImage(); }} />
            {pendingImage ? (
              <Button title="Remover foto escolhida" variant="outline" fullWidth disabled={saving}
                onPress={() => setPendingImage(null)} />
            ) : null}
            <Text style={styles.help}>JPG, PNG ou WEBP até 5 MB. A foto é enviada quando você salva.</Text>
          </>
        ) : null}

        {step === 4 ? (
          <View style={styles.review}>
            {reviewRow("Nome", values.name.trim(), 0)}
            {reviewRow("Categoria", categoryLabel(values.category), 0)}
            {reviewRow("Descrição resumida", values.shortDescription.trim(), 0)}
            {reviewRow("Preço regular", money(values.regularPrice), 1)}
            {reviewRow("Preço IDDUN", money(values.price), 1)}
            {reviewRow("Duração", values.duration.trim() ? `${values.duration.trim()} min` : "", 1)}
            {reviewRow("Local", establishmentName, 2)}
            {reviewRow("Foto", pendingImage ? "Nova foto escolhida" : currentImageUrl ? "Foto atual mantida" : "Sem foto", 3)}
          </View>
        ) : null}
      </View>

      <View style={styles.actions}>
        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
        {fetching ? <ActivityIndicator accessibilityLabel="Carregando serviço" /> : null}
        {step < LAST ? (
          <Button title="Continuar" fullWidth disabled={fetching || !editable} onPress={() => goTo(step + 1)} />
        ) : (
          <Button title={editId ? "Salvar alterações" : "Salvar rascunho"} fullWidth loading={saving}
            disabled={saving || fetching || !editable} onPress={() => { void submit(); }} />
        )}
        {step > 0 ? <Button title="Voltar" variant="outline" fullWidth disabled={saving} onPress={() => goTo(step - 1)} /> : null}
      </View>
    </ScrollView>
  );
}

const useStyles = makeStyles((colors) => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingTop: spacing.xxxl, paddingHorizontal: spacing.lg, paddingBottom: spacing.xxxl, gap: spacing.lg },
  backButton: { width: touch.minimum, height: touch.minimum, alignItems: "center" as const, justifyContent: "center" as const },
  heading: { color: colors.onSurface, fontSize: typography.title, fontWeight: "700" as const },
  description: { color: colors.onSurfaceSecondary, fontSize: typography.bodyLarge, lineHeight: 24 },
  progress: { flexDirection: "row" as const, justifyContent: "space-between" as const, gap: spacing.sm },
  progressDot: { flex: 1, minHeight: spacing.xxl, alignItems: "center" as const, justifyContent: "center" as const,
    borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border },
  progressDone: { borderColor: colors.plum },
  progressCurrent: { backgroundColor: colors.plum, borderColor: colors.plum },
  progressNumber: { color: colors.onSurfaceSecondary, fontSize: typography.body, fontWeight: "600" as const },
  progressNumberCurrent: { color: colors.white },
  section: { padding: spacing.xl, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, gap: spacing.md },
  stepCount: { color: colors.link, fontSize: typography.small, fontWeight: "700" as const, letterSpacing: 1, textTransform: "uppercase" as const },
  sectionTitle: { color: colors.onSurface, fontSize: typography.titleSmall, fontWeight: "700" as const },
  actions: { gap: spacing.md, paddingTop: spacing.sm },
  label: { color: colors.onSurface, fontSize: typography.bodyLarge, fontWeight: "600" as const, marginTop: spacing.sm },
  help: { color: colors.onSurfaceSecondary, fontSize: typography.body, lineHeight: 20 },
  input: { minHeight: touch.minimum, color: colors.onSurface, fontSize: typography.bodyLarge, borderColor: colors.border,
    borderWidth: 1, backgroundColor: colors.surface, borderRadius: radius.sm,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  multiline: { minHeight: 96, textAlignVertical: "top" as const },
  chips: { flexDirection: "row" as const, flexWrap: "wrap" as const, gap: spacing.sm },
  chip: { minHeight: touch.minimum, justifyContent: "center" as const, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm,
    paddingHorizontal: spacing.lg, paddingVertical: spacing.sm },
  chipSelected: { borderColor: colors.plum, backgroundColor: colors.plumSoft },
  chipText: { color: colors.onSurface, fontSize: typography.bodyLarge },
  note: { flexDirection: "row" as const, gap: spacing.md, padding: spacing.lg, borderRadius: radius.sm, backgroundColor: colors.surface },
  noteText: { flex: 1, color: colors.onSurface, fontSize: typography.body, lineHeight: 21 },
  review: { gap: spacing.xs },
  reviewRow: { flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.divider },
  reviewCopy: { flex: 1, gap: spacing.xs },
  reviewLabel: { color: colors.onSurfaceSecondary, fontSize: typography.body },
  reviewValue: { color: colors.onSurface, fontSize: typography.bodyLarge },
  reviewEdit: { minHeight: touch.minimum, minWidth: touch.minimum, justifyContent: "center" as const, alignItems: "flex-end" as const },
  reviewEditText: { color: colors.link, fontSize: typography.bodyLarge, fontWeight: "600" as const },
  fieldError: { color: colors.error, fontSize: typography.body },
  imagePreview: { width: "100%" as const, aspectRatio: 16 / 9, borderRadius: radius.md, backgroundColor: colors.surface },
  imageFallback: { width: "100%" as const, aspectRatio: 16 / 9, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border,
    alignItems: "center" as const, justifyContent: "center" as const, backgroundColor: colors.surface },
  imageFallbackText: { color: colors.onSurfaceSecondary, fontSize: typography.bodyLarge, fontWeight: "600" as const },
  error: { color: colors.error, fontSize: typography.body },
}));
