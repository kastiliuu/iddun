import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  createProfessionalServiceAvailability,
  createProfessionalSlotsBatch,
  createProfessionalSlotsFromSchedule,
  changeProfessionalSlotStatus,
  getProfessionalServiceAvailability,
  type ManagedAvailabilitySlot,
} from "@/api/services";
import { Button } from "@/components/Button";
import { BATCH_MAX_TIMES, SLOT_STATUS_LABELS, parseBatchTimes } from "@/services/serviceWizard";
import { makeStyles, spacing, useTheme } from "@/theme";

export default function ServiceAvailabilityScreen() {
  const router = useRouter();
  const { serviceId: rawId } = useLocalSearchParams<{ serviceId?: string }>();
  const serviceId = rawId && /^\d+$/.test(rawId) ? Number(rawId) : null;
  const { colors } = useTheme();
  const styles = useStyles();
  const [slots, setSlots] = useState<ManagedAvailabilitySlot[]>([]);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [batchTimes, setBatchTimes] = useState("");
  const [busy, setBusy] = useState(false);
  const [slotBusy, setSlotBusy] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!serviceId) throw new Error("Identificador do serviço inválido.");
    const response = await getProfessionalServiceAvailability(serviceId);
    setSlots(response.items);
  }, [serviceId]);

  useEffect(() => {
    let active = true;
    if (!serviceId) {
      Promise.resolve().then(() => {
        if (active) {
          setError("Identificador do serviço inválido.");
          setLoading(false);
        }
      });
      return () => { active = false; };
    }
    getProfessionalServiceAvailability(serviceId).then(
      result => { if (active) setSlots(result.items); },
      cause => {
        if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar os horários.");
      },
    ).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [serviceId]);

  const changeStatus = (slot: ManagedAvailabilitySlot, action: "block" | "reopen") => {
    if (!serviceId) return;
    Alert.alert(action === "block" ? "Bloquear horário?" : "Reabrir horário?",
      action === "block" ? "O horário deixará de aceitar reservas." : "O horário poderá voltar a receber reservas se ainda estiver válido.",
      [
        { text: "Cancelar", style: "cancel" },
        { text: "Confirmar", onPress: () => {
          setSlotBusy(slot.id);
          changeProfessionalSlotStatus(serviceId, slot.id, action).then(() => refresh())
            .catch(cause => Alert.alert("Erro ao atualizar horário", cause instanceof Error ? cause.message : "Tente novamente."))
            .finally(() => setSlotBusy(null));
        } },
      ],
    );
  };

  const createFromSchedule = () => {
    if (!serviceId) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      setError("Informe a data no formato AAAA-MM-DD.");
      return;
    }
    Alert.alert("Abrir horários da jornada?", "Serão usados os horários semanais já cadastrados, respeitando intervalos e disponibilidade.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Confirmar", onPress: () => {
        setBusy(true);
        setError(null);
        createProfessionalSlotsFromSchedule(serviceId, date).then(async ({ createdCount }) => {
          await refresh();
          Alert.alert("Horários criados", `${createdCount} horários gerados para a data selecionada.`);
        }).catch(cause => {
          setError(cause instanceof Error ? cause.message : "Não foi possível abrir os horários.");
        }).finally(() => setBusy(false));
      } },
    ]);
  };

  // V1-CONV-D06: vários horários num dia, tudo ou nada (como na Web).
  const submitBatch = async () => {
    if (!serviceId || busy) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      setError("Informe a data no formato AAAA-MM-DD.");
      return;
    }
    const parsed = parseBatchTimes(batchTimes);
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { createdCount } = await createProfessionalSlotsBatch(serviceId, date, parsed.times);
      await refresh();
      setBatchTimes("");
      Alert.alert("Horários abertos", `${createdCount} horários disponibilizados para reserva.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Nenhum horário do lote foi criado. Tente novamente.");
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!serviceId) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) {
      setError("Informe a data AAAA-MM-DD e o horário HH:MM.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createProfessionalServiceAvailability(serviceId, { date, time });
      await refresh();
      setTime("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível abrir o horário.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Pressable accessibilityRole="button" onPress={() => router.back()}>
        <Text style={styles.link}>Voltar</Text>
      </Pressable>
      <Text style={styles.heading}>Horários do serviço</Text>
      <Button title="Configurar jornada semanal" variant="secondary" onPress={() => router.push("/weekly-schedule")} />
      <Text style={styles.subtle}>Horários são criados no fuso do perfil profissional e passam pelas validações de agenda do IDDUN.</Text>
      <Text style={styles.label}>Data (AAAA-MM-DD)</Text>
      <TextInput style={styles.input} value={date} onChangeText={setDate}
        accessibilityLabel="Data do horário" autoCapitalize="none"
        placeholder="2026-11-05" placeholderTextColor={colors.muted} />
      <Text style={styles.label}>Hora (HH:MM)</Text>
      <TextInput style={styles.input} value={time} onChangeText={setTime}
        accessibilityLabel="Hora do atendimento" keyboardType="numbers-and-punctuation"
        placeholder="14:30" placeholderTextColor={colors.muted} />
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Button title={busy ? "Salvando..." : "Abrir horário"} fullWidth
        disabled={busy || loading || !serviceId} onPress={() => { void submit(); }} />
      <Text style={styles.label}>Vários horários na mesma data</Text>
      <TextInput style={[styles.input, styles.multiline]} value={batchTimes} onChangeText={setBatchTimes}
        accessibilityLabel="Horários do lote" accessibilityHint={`Separe até ${BATCH_MAX_TIMES} horários por vírgulas ou linhas`}
        multiline autoCapitalize="none" keyboardType="numbers-and-punctuation"
        placeholder="09:00, 10:00, 11:00" placeholderTextColor={colors.muted} />
      <Text style={styles.subtle}>{`Até ${BATCH_MAX_TIMES} horários. Se algum conflitar, nenhum horário do lote é criado.`}</Text>
      <Button title="Abrir horários em lote" fullWidth variant="secondary"
        disabled={busy || loading || !serviceId} onPress={() => { void submitBatch(); }} />
      <Button title="Gerar horários da jornada semanal" fullWidth
        variant="secondary" disabled={busy || loading || !serviceId}
        onPress={createFromSchedule} />
      <Text style={styles.subtle}>Esta ação usa a jornada semanal cadastrada no seu perfil para a data escolhida. Não altera suas regras de trabalho.</Text>
      <Text style={styles.section}>Próximos horários</Text>
      {loading ? <ActivityIndicator accessibilityLabel="Carregando horários" /> :
        slots.length === 0 ? <Text style={styles.subtle}>Nenhum horário futuro cadastrado.</Text> :
          slots.map(slot => (
            <View key={slot.id} style={styles.slot}>
              <Text style={styles.label}>{slot.startsAt.replace("T", " ").slice(0, 16)}</Text>
              <Text style={styles.subtle}>{SLOT_STATUS_LABELS[slot.status] ?? slot.status}</Text>
              {(slot.status === "available" || slot.status === "blocked_manual") ? (
                <Pressable accessibilityRole="button" disabled={slotBusy !== null}
                  accessibilityLabel={(slot.status === "available" ? "Bloquear " : "Reabrir ") + slot.startsAt}
                  onPress={() => changeStatus(slot, slot.status === "available" ? "block" : "reopen")}
                  style={{ paddingVertical: spacing.sm }}>
                  <Text style={styles.link}>{slotBusy === slot.id ? "Salvando..." : slot.status === "available" ? "Bloquear horário" : "Reabrir horário"}</Text>
                </Pressable>
              ) : null}
            </View>
          ))}
    </ScrollView>
  );
}

const useStyles = makeStyles(colors => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingTop: 56, paddingBottom: 48, paddingHorizontal: spacing.lg, gap: spacing.md },
  link: { color: colors.link, fontWeight: "600" as const, paddingVertical: spacing.sm },
  heading: { color: colors.onSurface, fontSize: 26, fontWeight: "700" as const },
  section: { color: colors.onSurface, fontSize: 20, fontWeight: "700" as const, marginTop: spacing.lg },
  subtle: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  label: { color: colors.onSurface, fontSize: 14, fontWeight: "600" as const },
  input: { color: colors.onSurface, minHeight: 50, borderRadius: 12,
    borderWidth: 1, borderColor: colors.glassBorder, backgroundColor: colors.surfaceSecondary,
    paddingHorizontal: spacing.md },
  error: { color: colors.error, fontSize: 14 },
  multiline: { minHeight: 88, paddingVertical: spacing.sm, textAlignVertical: "top" as const },
  slot: { padding: spacing.md, borderRadius: 12, borderWidth: 1,
    borderColor: colors.glassBorder, gap: spacing.xs },
}));
