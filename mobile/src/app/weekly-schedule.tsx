import React, { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Switch, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import {
  getProfessionalWeeklySchedule,
  updateProfessionalWeeklySchedule,
  type WeeklyScheduleDay,
} from "@/api/services";
import { Button } from "@/components/Button";
import { makeStyles, spacing, useTheme } from "@/theme";

export default function WeeklyScheduleScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useStyles();
  const [days, setDays] = useState<WeeklyScheduleDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let active = true;
    getProfessionalWeeklySchedule().then(({ days: value }) => {
      if (active) setDays(value);
    }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar a jornada.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const change = (weekday: number, updates: Partial<WeeklyScheduleDay>) => {
    setSuccess(false);
    setDays(current => current.map(day => day.weekday === weekday ? { ...day, ...updates } : day));
  };

  const save = async () => {
    if (saving) return;
    setError(null);
    setSaving(true);
    try {
      const response = await updateProfessionalWeeklySchedule(days);
      setDays(response.days);
      setSuccess(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível salvar a jornada.");
    } finally {
      setSaving(false);
    }
  };

  const timeInput = (day: WeeklyScheduleDay, field: "start" | "end" | "break_start" | "break_end", label: string) => (
    <View style={styles.timeField}>
      <Text style={styles.subtle}>{label}</Text>
      <TextInput value={day[field]} onChangeText={value => change(day.weekday, { [field]: value })}
        style={styles.input} maxLength={5} keyboardType="numbers-and-punctuation"
        accessibilityLabel={`${day.label} — ${label}`} placeholder="HH:MM" placeholderTextColor={colors.muted} />
    </View>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Button title="Voltar" variant="ghost" onPress={() => router.back()} />
      <Text style={styles.heading}>Jornada semanal</Text>
      <Text style={styles.subtle}>Defina os dias de trabalho e intervalos. Alterar a jornada não cancela reservas ou horários já criados.</Text>
      {loading ? <ActivityIndicator accessibilityLabel="Carregando jornada" /> :
        days.map(day => (
          <View key={day.weekday} style={styles.day}>
            <View style={styles.toggle}>
              <Text style={styles.dayTitle}>{day.label}</Text>
              <Switch value={day.enabled} onValueChange={enabled => change(day.weekday, { enabled })}
                accessibilityLabel={`Trabalhar ${day.label}`} />
            </View>
            {day.enabled ? (
              <>
                <View style={styles.times}>
                  {timeInput(day, "start", "Início")}
                  {timeInput(day, "end", "Fim")}
                </View>
                <View style={styles.toggle}>
                  <Text style={styles.subtle}>Intervalo</Text>
                  <Switch value={day.break_enabled} onValueChange={break_enabled => change(day.weekday, { break_enabled })}
                    accessibilityLabel={`Intervalo de ${day.label}`} />
                </View>
                {day.break_enabled ? (
                  <View style={styles.times}>
                    {timeInput(day, "break_start", "Início do intervalo")}
                    {timeInput(day, "break_end", "Fim do intervalo")}
                  </View>
                ) : null}
              </>
            ) : null}
          </View>
        ))}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {success ? <Text accessibilityRole="alert" style={styles.success}>Jornada atualizada.</Text> : null}
      <Button title={saving ? "Salvando..." : "Salvar jornada"} disabled={loading || saving || days.length !== 7}
        onPress={() => { void save(); }} fullWidth />
    </ScrollView>
  );
}

const useStyles = makeStyles(colors => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingTop: 56, paddingBottom: 48, paddingHorizontal: spacing.lg, gap: spacing.md },
  heading: { color: colors.onSurface, fontSize: 28, fontWeight: "700" as const },
  subtle: { color: colors.muted, fontSize: 13, lineHeight: 20 },
  day: { borderWidth: 1, borderColor: colors.glassBorder, borderRadius: 14,
    padding: spacing.md, gap: spacing.md, backgroundColor: colors.surfaceSecondary },
  dayTitle: { color: colors.onSurface, fontSize: 16, fontWeight: "600" as const },
  toggle: { flexDirection: "row" as const, alignItems: "center" as const, justifyContent: "space-between" as const },
  times: { flexDirection: "row" as const, gap: spacing.md },
  timeField: { flex: 1, gap: spacing.xs },
  input: { borderWidth: 1, borderColor: colors.glassBorder, borderRadius: 10, color: colors.onSurface,
    paddingHorizontal: spacing.md, minHeight: 44 },
  error: { color: colors.error },
  success: { color: colors.success },
}));
