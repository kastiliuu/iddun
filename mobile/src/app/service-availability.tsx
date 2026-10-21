import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  createProfessionalServiceAvailability,
  getProfessionalServiceAvailability,
  type ManagedAvailabilitySlot,
} from "@/api/services";
import { Button } from "@/components/Button";
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
  const [busy, setBusy] = useState(false);
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
      <Text style={styles.section}>Próximos horários</Text>
      {loading ? <ActivityIndicator accessibilityLabel="Carregando horários" /> :
        slots.length === 0 ? <Text style={styles.subtle}>Nenhum horário futuro cadastrado.</Text> :
          slots.map(slot => (
            <View key={slot.id} style={styles.slot}>
              <Text style={styles.label}>{slot.startsAt.replace("T", " ").slice(0, 16)}</Text>
              <Text style={styles.subtle}>{slot.status}</Text>
            </View>
          ))}
    </ScrollView>
  );
}

const useStyles = makeStyles(colors => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingTop: 56, paddingBottom: 48, paddingHorizontal: spacing.lg, gap: spacing.md },
  link: { color: colors.plum, fontWeight: "600" as const, paddingVertical: spacing.sm },
  heading: { color: colors.onSurface, fontSize: 26, fontWeight: "700" as const },
  section: { color: colors.onSurface, fontSize: 20, fontWeight: "700" as const, marginTop: spacing.lg },
  subtle: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  label: { color: colors.onSurface, fontSize: 14, fontWeight: "600" as const },
  input: { color: colors.onSurface, minHeight: 50, borderRadius: 12,
    borderWidth: 1, borderColor: colors.glassBorder, backgroundColor: colors.surfaceSecondary,
    paddingHorizontal: spacing.md },
  error: { color: colors.error, fontSize: 14 },
  slot: { padding: spacing.md, borderRadius: 12, borderWidth: 1,
    borderColor: colors.glassBorder, gap: spacing.xs },
}));
