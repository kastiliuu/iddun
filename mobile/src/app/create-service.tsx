import React, { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";

import { createProfessionalServiceDraft } from "@/api/services";
import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import { makeStyles, spacing, touch, useTheme } from "@/theme";

const categories = [
  ["cabelo", "Cabelo"],
  ["unhas", "Unhas"],
  ["barbearia", "Barbearia"],
  ["estetica", "Estética"],
  ["tatuagem", "Tatuagem"],
  ["sobrancelhas", "Sobrancelhas"],
] as const;

export default function CreateServiceScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useStyles();
  const [name, setName] = useState("");
  const [category, setCategory] = useState<string>("unhas");
  const [shortDescription, setShortDescription] = useState("");
  const [price, setPrice] = useState("");
  const [duration, setDuration] = useState("60");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const value = Number(price.replace(",", "."));
    const minutes = Number(duration);
    if (!name.trim() || name.trim().length > 160 || !shortDescription.trim() ||
        shortDescription.trim().length > 220 || !price.trim() ||
        !Number.isFinite(value) || value < 0 || !Number.isInteger(minutes) ||
        minutes < 10 || minutes > 720) {
      setError("Preencha nome, descrição, preço e duração válida (10 a 720 minutos).");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createProfessionalServiceDraft({
        name: name.trim(),
        category,
        shortDescription: shortDescription.trim(),
        price: value,
        regularPrice: value,
        durationMinutes: minutes,
      });
      router.replace("/manage-services");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível salvar o serviço.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Pressable accessibilityRole="button" accessibilityLabel="Voltar"
        onPress={() => router.canGoBack() ? router.back() : router.replace("/(tabs)/create")}
        style={styles.backButton}>
        <Icon name="arrow-left" size={20} color={colors.onSurface} />
      </Pressable>
      <Text style={styles.heading}>Novo serviço</Text>
      <Text style={styles.description}>Crie um rascunho privado. Você poderá completar e publicar depois.</Text>
      <Text style={styles.label}>Nome do serviço *</Text>
      <TextInput accessibilityLabel="Nome do serviço" value={name} onChangeText={setName}
        maxLength={160} placeholder="Ex.: Banho de gel" placeholderTextColor={colors.muted} style={styles.input} />
      <Text style={styles.label}>Categoria *</Text>
      <View style={styles.categories}>
        {categories.map(([key, label]) => (
          <Pressable key={key} accessibilityRole="button"
            accessibilityState={{ selected: category === key }}
            onPress={() => setCategory(key)} style={[styles.chip, category === key && styles.chipSelected]}>
            <Text style={styles.chipText}>{label}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.label}>Descrição resumida *</Text>
      <TextInput accessibilityLabel="Descrição resumida" value={shortDescription}
        onChangeText={setShortDescription} maxLength={220} multiline
        placeholder="Conte o que está incluído" placeholderTextColor={colors.muted}
        style={[styles.input, styles.multiline]} />
      <Text style={styles.label}>Preço (R$) *</Text>
      <TextInput accessibilityLabel="Preço em reais" value={price} onChangeText={setPrice}
        keyboardType="decimal-pad" placeholder="120,00" placeholderTextColor={colors.muted} style={styles.input} />
      <Text style={styles.label}>Duração em minutos *</Text>
      <TextInput accessibilityLabel="Duração em minutos" value={duration} onChangeText={setDuration}
        keyboardType="number-pad" placeholder="60" placeholderTextColor={colors.muted} style={styles.input} />
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {saving ? <ActivityIndicator accessibilityLabel="Salvando rascunho" /> : null}
      <Button title="Salvar rascunho" fullWidth disabled={saving} onPress={() => { void submit(); }} />
    </ScrollView>
  );
}

const useStyles = makeStyles((colors) => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingTop: 54, paddingHorizontal: spacing.lg, paddingBottom: 48, gap: spacing.md },
  backButton: { width: touch.minimum, height: touch.minimum, alignItems: "center" as const,
    justifyContent: "center" as const },
  heading: { color: colors.onSurface, fontSize: 28, fontWeight: "700" as const },
  description: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  label: { color: colors.onSurface, fontSize: 14, fontWeight: "600" as const },
  input: { minHeight: 50, color: colors.onSurface, borderColor: colors.glassBorder,
    borderWidth: 1, backgroundColor: colors.surfaceSecondary, borderRadius: 12,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  multiline: { minHeight: 90, textAlignVertical: "top" as const },
  categories: { flexDirection: "row" as const, flexWrap: "wrap" as const, gap: spacing.sm },
  chip: { borderWidth: 1, borderColor: colors.glassBorder, borderRadius: 20,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  chipSelected: { borderColor: colors.plum, backgroundColor: colors.plumSoft },
  chipText: { color: colors.onSurface },
  error: { color: colors.error, fontSize: 13 },
}));
