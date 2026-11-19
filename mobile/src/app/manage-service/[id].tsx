import React, { useCallback, useState } from "react";
import { ActivityIndicator, Alert, Image, Pressable, ScrollView, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";

import { ApiError } from "@/api/client";
import {
  changeProfessionalServiceStatus,
  getProfessionalServiceAvailability,
  getProfessionalServiceDetail,
  getProfessionalServiceEstablishments,
  type ManagedAvailabilitySlot,
  type ProfessionalServiceDetail,
} from "@/api/services";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { SERVICE_STATUS_LABELS, SLOT_STATUS_LABELS, categoryLabel, formatMoney } from "@/services/serviceWizard";
import { makeStyles, radius, spacing, touch, typography, useTheme } from "@/theme";

/*
 * P-003 · detalhe do serviço no app (lista → detalhe → horários).
 * Mostra só dados reais do próprio serviço e as ações que o estado
 * permite: rascunho/pausado edita e publica; publicado pausa e abre
 * horários. O status exibido é sempre o que o servidor confirmou.
 */
export default function ManageServiceDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const serviceId = id && /^\d+$/.test(id) ? Number(id) : null;
  const { colors } = useTheme();
  const styles = useStyles();
  const [service, setService] = useState<ProfessionalServiceDetail | null>(null);
  const [place, setPlace] = useState("Atendimento independente");
  const [slots, setSlots] = useState<ManagedAvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let active = true;
    if (!serviceId) {
      Promise.resolve().then(() => {
        if (active) { setError("Serviço inválido."); setLoading(false); }
      });
      return () => { active = false; };
    }
    setError(null);
    Promise.all([
      getProfessionalServiceDetail(serviceId),
      getProfessionalServiceAvailability(serviceId).catch(() => ({ items: [] as ManagedAvailabilitySlot[] })),
      getProfessionalServiceEstablishments().catch(() => ({ items: [] })),
    ]).then(([detail, availability, establishments]) => {
      if (!active) return;
      setService(detail.service);
      setSlots(availability.items.slice(0, 3));
      const linked = establishments.items.find(item => item.id === detail.service.establishmentId);
      setPlace(detail.service.establishmentId === null ? "Atendimento independente" : linked?.name ?? "Estabelecimento vinculado");
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar o serviço.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [serviceId]);

  useFocusEffect(load);

  const changeStatus = (action: "publish" | "pause") => {
    if (!serviceId || !service || pending) return;
    Alert.alert(
      action === "pause" ? "Pausar serviço?" : "Publicar serviço?",
      action === "pause"
        ? "Novas reservas ficam indisponíveis. Reservas confirmadas continuam válidas."
        : "O serviço aparece no catálogo e só recebe reservas em horários válidos.",
      [
        { text: "Cancelar", style: "cancel" },
        { text: "Confirmar", onPress: () => {
          setPending(true);
          changeProfessionalServiceStatus(serviceId, action)
            .then(() => load())
            .catch((cause) => {
              const message = cause instanceof ApiError && cause.status === 429
                ? "Muitas tentativas. Aguarde um pouco e tente de novo."
                : cause instanceof Error ? cause.message : "Tente novamente.";
              Alert.alert("Não foi possível alterar o serviço", message);
            })
            .finally(() => setPending(false));
        } },
      ],
    );
  };

  const back = () => router.canGoBack() ? router.back() : router.replace("/manage-services");

  if (loading) {
    return <View style={styles.container}><ActivityIndicator accessibilityLabel="Carregando serviço" style={styles.loading} /></View>;
  }
  if (error || !service) {
    return (
      <View style={styles.container}>
        <EmptyState title="Serviço indisponível" description={error ?? "Não foi possível carregar o serviço."}
          actionLabel="Voltar para Meus serviços" onActionPress={() => router.replace("/manage-services")} />
      </View>
    );
  }

  const status = SERVICE_STATUS_LABELS[service.status] ?? service.status;
  const editable = service.status === "draft" || service.status === "paused";
  const published = service.status === "published";

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Pressable accessibilityRole="button" accessibilityLabel="Voltar para Meus serviços" onPress={back} style={styles.backButton}>
        <Icon name="arrow-left" size={20} color={colors.onSurface} />
      </Pressable>

      <View style={styles.headerCopy}>
        <Text style={styles.kicker}>Serviço</Text>
        <Text accessibilityRole="header" style={styles.title}>{service.name}</Text>
        <Text style={styles.meta}>{categoryLabel(service.category)} · {place}</Text>
        <View style={[styles.status, published && styles.statusPublished]}>
          <Text style={styles.statusText}>{status}</Text>
        </View>
      </View>

      {service.imageUrl ? (
        <Image source={{ uri: service.imageUrl }} accessibilityLabel={`Foto de ${service.name}`}
          style={styles.cover} resizeMode="cover" />
      ) : null}

      <View style={styles.facts}>
        <View style={styles.fact}><Text style={styles.factLabel}>Preço IDDUN</Text><Text style={styles.factValue}>{formatMoney(service.price)}</Text></View>
        {service.regularPrice !== service.price ? (
          <View style={styles.fact}><Text style={styles.factLabel}>Preço regular</Text><Text style={styles.factValue}>{formatMoney(service.regularPrice)}</Text></View>
        ) : null}
        <View style={styles.fact}><Text style={styles.factLabel}>Duração</Text><Text style={styles.factValue}>{service.durationMinutes} min</Text></View>
      </View>
      <Text style={styles.body}>{service.shortDescription}</Text>

      <View style={styles.section}>
        <Text accessibilityRole="header" style={styles.sectionTitle}>Disponibilidade</Text>
        {published ? (
          slots.length ? (
            <View style={styles.slots}>
              {slots.map(slot => (
                <Text key={slot.id} style={styles.slot}>
                  {slot.startsAt.replace("T", " ").slice(0, 16)} · {SLOT_STATUS_LABELS[slot.status] ?? slot.status}
                </Text>
              ))}
            </View>
          ) : <Text style={styles.body}>Nenhum horário futuro cadastrado. Abra um horário para receber reservas.</Text>
        ) : (
          <Text style={styles.body}>Este serviço não está disponível para reservas enquanto estiver {status.toLowerCase()}.</Text>
        )}
        {published ? (
          <Button title="Gerenciar horários" fullWidth
            onPress={() => router.push({ pathname: "/service-availability", params: { serviceId: String(service.id) } })} />
        ) : null}
      </View>

      <View style={styles.actions}>
        {editable ? (
          <>
            <Button title={service.status === "paused" ? "Republicar serviço" : "Publicar serviço"} fullWidth
              loading={pending} disabled={pending} onPress={() => changeStatus("publish")} />
            <Button title="Editar serviço" variant="outline" fullWidth disabled={pending}
              onPress={() => router.push({ pathname: "/create-service", params: { editId: String(service.id) } })} />
          </>
        ) : null}
        {published ? (
          <>
            <Button title="Pausar serviço" variant="outline" fullWidth loading={pending} disabled={pending}
              onPress={() => changeStatus("pause")} />
            <Text style={styles.help}>Serviços publicados não são editados para não mudar as condições de reservas existentes. Pause para editar.</Text>
          </>
        ) : null}
      </View>
    </ScrollView>
  );
}

const useStyles = makeStyles((colors) => ({
  container: { flex: 1, backgroundColor: colors.surface },
  loading: { marginTop: spacing.xxxl },
  content: { paddingTop: spacing.xxxl, paddingHorizontal: spacing.lg, paddingBottom: spacing.xxxl, gap: spacing.lg },
  backButton: { width: touch.minimum, height: touch.minimum, alignItems: "center" as const, justifyContent: "center" as const,
    borderRadius: radius.pill, backgroundColor: colors.glassSoft, borderWidth: 1, borderColor: colors.glassBorder },
  headerCopy: { gap: spacing.sm, alignItems: "flex-start" as const },
  kicker: { color: colors.plum, fontSize: typography.small, fontWeight: "700" as const, letterSpacing: 1, textTransform: "uppercase" as const },
  title: { color: colors.onSurface, fontSize: typography.title, fontWeight: "700" as const },
  meta: { color: colors.onSurfaceSecondary, fontSize: typography.body },
  status: { paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border },
  statusPublished: { borderColor: colors.success },
  statusText: { color: colors.onSurface, fontSize: typography.small, fontWeight: "600" as const },
  cover: { width: "100%" as const, aspectRatio: 16 / 9, borderRadius: radius.md, backgroundColor: colors.surfaceSecondary },
  facts: { flexDirection: "row" as const, flexWrap: "wrap" as const, gap: spacing.sm },
  fact: { flexGrow: 1, minWidth: 96, padding: spacing.md, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, gap: spacing.xs },
  factLabel: { color: colors.onSurfaceSecondary, fontSize: typography.small },
  factValue: { color: colors.onSurface, fontSize: typography.bodyLarge, fontWeight: "600" as const },
  body: { color: colors.onSurface, fontSize: typography.body, lineHeight: 21 },
  section: { gap: spacing.md, padding: spacing.lg, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceSecondary },
  sectionTitle: { color: colors.onSurface, fontSize: typography.titleSmall, fontWeight: "700" as const },
  slots: { gap: spacing.sm },
  slot: { color: colors.onSurface, fontSize: typography.body },
  actions: { gap: spacing.md },
  help: { color: colors.onSurfaceSecondary, fontSize: typography.body, lineHeight: 21 },
}));
