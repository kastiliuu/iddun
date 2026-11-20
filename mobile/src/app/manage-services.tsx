import React, { useCallback, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";

import { getManagedServices, type ManagedService } from "@/api/services";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { createLatestRequestGate } from "@/services/latestRequestGate";
import { SERVICE_STATUS_LABELS, categoryLabel, formatMoney } from "@/services/serviceWizard";
import { makeStyles, radius, spacing, touch, typography, useTheme } from "@/theme";

/*
 * P-003 · Catálogo C no app: lista → detalhe → horários. Cada linha mostra
 * nome, categoria, preço, duração e status verdadeiros; as ações ficam no
 * detalhe do serviço, uma tela por vez.
 */
export default function ManageServicesScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const [items, setItems] = useState<ManagedService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const requestGate = useRef(createLatestRequestGate());

  const reload = useCallback(() => {
    // Retry ou retorno ao catálogo invalida qualquer leitura anterior.
    const currentRequest = requestGate.current.begin();
    setLoading(true);
    setError(null);
    getManagedServices().then(
      (response) => {
        if (requestGate.current.isCurrent(currentRequest)) {
          setItems(response.items);
        }
      },
      (cause) => {
        if (requestGate.current.isCurrent(currentRequest)) {
          setError(cause instanceof Error ? cause.message : "Não foi possível carregar seus serviços.");
        }
      },
    ).finally(() => {
      if (requestGate.current.isCurrent(currentRequest)) {
        setLoading(false);
      }
    });
    return () => {
      // Blur ou desmontagem invalidam também retries iniciados nesta tela.
      requestGate.current.invalidateAll();
    };
  }, []);

  // Volta do detalhe ou do cadastro: a lista reflete o que o servidor confirmou.
  useFocusEffect(reload);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Voltar"
          onPress={() => router.canGoBack() ? router.back() : router.replace("/create")}
          style={styles.backButton}>
          <Icon name="arrow-left" size={20} color={colors.onSurface} />
        </Pressable>
      </View>
      <View style={styles.titleRow}>
        <View style={styles.titleCopy}>
          <Text accessibilityRole="header" style={styles.title}>Meus serviços</Text>
          <Text style={styles.subtitle}>Toque em um serviço para ver detalhes e horários.</Text>
        </View>
        <Pressable accessibilityRole="button" accessibilityLabel="Criar serviço"
          onPress={() => router.push("/create-service")} style={styles.createButton}>
          <Icon name="plus" size={18} color={colors.onBrand} />
          <Text style={styles.createText}>Criar</Text>
        </Pressable>
      </View>

      {loading ? (
        <ActivityIndicator accessibilityLabel="Carregando serviços" style={styles.loading} />
      ) : error ? (
        <EmptyState
          title="Não foi possível carregar seus serviços"
          description={error}
          actionLabel="Tentar novamente"
          onActionPress={() => { reload(); }}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="Você ainda não possui serviços"
          description="O catálogo está vazio. Seus serviços reais aparecerão aqui assim que forem cadastrados."
          actionLabel="Criar primeiro serviço"
          onActionPress={() => router.push("/create-service")}
        />
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          <Text style={styles.count}>{items.length} {items.length === 1 ? "serviço" : "serviços"}</Text>
          {items.map(item => {
            const status = SERVICE_STATUS_LABELS[item.status] ?? item.status;
            return (
              <Pressable key={item.id} accessibilityRole="button"
                accessibilityLabel={`${item.title}, ${categoryLabel(item.category)}, ${formatMoney(item.price)}, ${item.durationMinutes} minutos, ${status}`}
                accessibilityHint="Abre os detalhes do serviço"
                onPress={() => router.push({ pathname: "/manage-service/[id]", params: { id: String(item.id) } })}
                style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}>
                <View style={styles.cardCopy}>
                  <Text style={styles.cardTitle}>{item.title}</Text>
                  <Text style={styles.cardMeta}>{categoryLabel(item.category)} · {formatMoney(item.price)} · {item.durationMinutes} min</Text>
                  <View style={[styles.status, item.status === "published" && styles.statusPublished]}>
                    <Text style={styles.statusText}>{status}</Text>
                  </View>
                </View>
                <Icon name="chevron-right" size={20} color={colors.onSurfaceSecondary} />
              </Pressable>
            );
          })}
        </ScrollView>
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: { flex: 1, backgroundColor: colors.surface },
  header: { paddingTop: spacing.xxxl, paddingHorizontal: spacing.lg },
  titleRow: { padding: spacing.lg, gap: spacing.lg, flexDirection: "row" as const, alignItems: "center" as const, justifyContent: "space-between" as const },
  titleCopy: { flex: 1, gap: spacing.sm },
  title: { color: colors.onSurface, fontSize: typography.title, fontWeight: "700" as const },
  subtitle: { color: colors.onSurfaceSecondary, fontSize: typography.body, lineHeight: 24 },
  createButton: { minHeight: touch.minimum, flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.sm,
    paddingHorizontal: spacing.lg, borderRadius: radius.sm, backgroundColor: colors.brand },
  createText: { color: colors.onBrand, fontSize: typography.bodyLarge, fontWeight: "600" as const },
  loading: { marginTop: spacing.xxl },
  list: { padding: spacing.lg, paddingBottom: spacing.xxxl, gap: spacing.md },
  count: { color: colors.onSurfaceSecondary, fontSize: typography.body },
  card: { minHeight: touch.minimum, flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.md,
    padding: spacing.lg, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surfaceSecondary },
  cardPressed: { borderColor: colors.plum },
  cardCopy: { flex: 1, gap: spacing.xs, alignItems: "flex-start" as const },
  cardTitle: { color: colors.onSurface, fontSize: typography.bodyLarge, fontWeight: "700" as const },
  cardMeta: { color: colors.onSurfaceSecondary, fontSize: typography.body, lineHeight: 20 },
  status: { marginTop: spacing.xs, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderRadius: radius.sm,
    borderWidth: 1, borderColor: colors.border },
  statusPublished: { borderColor: colors.success },
  statusText: { color: colors.onSurface, fontSize: typography.small, fontWeight: "600" as const },
  backButton: { width: touch.minimum, height: touch.minimum, alignItems: "center" as const, justifyContent: "center" as const,
    borderRadius: radius.pill, backgroundColor: colors.glassSoft, borderWidth: 1, borderColor: colors.glassBorder },
}));
