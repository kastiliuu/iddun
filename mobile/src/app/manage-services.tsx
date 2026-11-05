import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import {
  useRouter,
} from "expo-router";

import { changeProfessionalServiceStatus, getManagedServices, type ManagedService } from "@/api/services";

import {
  EmptyState,
} from "@/components/EmptyState";
import {
  Icon,
} from "@/components/Icon";

import {
  makeStyles,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function ManageServicesScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const [items, setItems] = useState<ManagedService[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getManagedServices();
      setItems(response.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível carregar seus serviços.");
    } finally {
      setLoading(false);
    }
  }, []);
  const setStatus = (item: ManagedService, action: "publish" | "pause") => {
    Alert.alert(
      action === "pause" ? "Pausar serviço?" : "Publicar serviço?",
      action === "pause"
        ? "O serviço deixará de aparecer para novas reservas. Reservas existentes continuam válidas."
        : "O serviço aparecerá no catálogo, mas só poderá receber reservas com horários válidos.",
      [
        { text: "Cancelar", style: "cancel" },
        { text: "Confirmar", onPress: () => {
          setPendingId(item.id);
          changeProfessionalServiceStatus(item.id, action)
            .then(() => reload())
            .catch((cause) => {
              Alert.alert("Não foi possível alterar o serviço", cause instanceof Error ? cause.message : "Tente novamente.");
            })
            .finally(() => setPendingId(null));
        }},
      ],
    );
  };

  useEffect(() => {
    let active = true;
    getManagedServices().then(
      (response) => {
        if (active) setItems(response.items);
      },
      (cause) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Não foi possível carregar seus serviços.");
        }
      },
    ).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Voltar"
          onPress={() => {
            if (router.canGoBack()) {
              router.back();
            } else {
              router.replace(
                "/create",
              );
            }
          }}
          style={styles.backButton}
        >
          <Icon
            name="arrow-left"
            size={20}
            color={colors.onSurface}
          />
        </Pressable>
      </View>
      <View style={styles.titleRow}>
        <View style={styles.titleCopy}>
          <Text style={styles.title}>Meus serviços</Text>
          <Text style={styles.subtitle}>Gerencie seu catálogo, publicações e horários.</Text>
        </View>
        <Pressable accessibilityRole="button" accessibilityLabel="Criar serviço"
          onPress={() => router.push("/create-service")} style={styles.createButton}>
          <Icon name="plus" size={18} color={colors.onBrand} />
          <Text style={styles.createText}>Criar</Text>
        </Pressable>
      </View>

      {loading ? (
        <ActivityIndicator accessibilityLabel="Carregando serviços" style={{ marginTop: 40 }} />
      ) : error ? (
        <EmptyState
          title="Não foi possível carregar seus serviços"
          description={error}
          actionLabel="Tentar novamente"
          onActionPress={() => { void reload(); }}
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
          <Text style={styles.count}>{items.length} {items.length === 1 ? "serviço cadastrado" : "serviços cadastrados"}</Text>
          {items.map(item => (
            <View key={item.id} style={styles.card}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardMeta}>{item.category} · {item.durationMinutes} min · R$ {item.price.toFixed(2).replace(".", ",")}</Text>
              {(item.status === "draft" || item.status === "paused") ? (
                <Pressable accessibilityRole="button" accessibilityLabel={`Editar ${item.title}`}
                  onPress={() => router.push({ pathname: "/create-service", params: { editId: String(item.id) } })}
                  style={styles.actionButton}>
                  <Text style={styles.actionText}>Editar serviço</Text>
                </Pressable>
              ) : null}
              {item.status !== "archived" ? (
                <Pressable accessibilityRole="button"
                  accessibilityLabel={item.status === "published" ? `Pausar ${item.title}` : `Publicar ${item.title}`}
                  accessibilityState={{ disabled: pendingId !== null }}
                  disabled={pendingId !== null}
                  onPress={() => setStatus(item, item.status === "published" ? "pause" : "publish")}
                  style={styles.actionButton}>
                  <Text style={styles.actionText}>
                    {pendingId === item.id ? "Salvando..." : item.status === "published" ? "Pausar serviço" : "Publicar serviço"}
                  </Text>
                </Pressable>
              ) : null}
              <Pressable accessibilityRole="button"
                accessibilityLabel={`Gerenciar horários de ${item.title}`}
                onPress={() => router.push({ pathname: "/service-availability", params: { serviceId: String(item.id) } })}
                style={styles.actionButton}>
                <Text style={styles.actionText}>Ver horários</Text>
              </Pressable>
              <Text style={styles.status}>
                {item.status === "published" ? "Publicado" : item.status === "draft" ? "Rascunho" : item.status === "paused" ? "Pausado" : "Arquivado"}
              </Text>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const useStyles = makeStyles(
  (colors) => ({
    container: {
      flex: 1,
      backgroundColor:
        colors.surface,
    },

    header: { paddingTop: spacing.xxxl, paddingHorizontal: spacing.lg },
    titleRow: { padding: spacing.lg, gap: spacing.lg, flexDirection: "row" as const, alignItems: "center" as const, justifyContent: "space-between" as const },
    titleCopy: { flex: 1, gap: spacing.sm },
    title: { color: colors.onSurface, fontSize: 24, fontWeight: "700" as const },
    subtitle: { color: colors.onSurfaceSecondary, fontSize: 14, lineHeight: 24 },
    createButton: { minHeight: touch.minimum, flexDirection: "row" as const, alignItems: "center" as const, gap: spacing.sm, paddingHorizontal: spacing.lg, borderRadius: 12, backgroundColor: colors.brand },
    createText: { color: colors.onBrand, fontSize: 16, fontWeight: "600" as const },
    list: { padding: spacing.lg, paddingBottom: spacing.xxxl, gap: spacing.lg },
    count: { color: colors.onSurfaceSecondary, fontSize: 14 },
    card: { padding: spacing.xl, gap: spacing.md, borderWidth: 1, borderColor: colors.border, borderRadius: 16, backgroundColor: colors.surfaceSecondary },
    cardTitle: { color: colors.onSurface, fontSize: 20, fontWeight: "700" as const },
    cardMeta: { color: colors.onSurfaceSecondary, fontSize: 16, lineHeight: 24 },
    actionButton: { minHeight: touch.minimum, justifyContent: "center" as const, borderRadius: 12, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.lg },
    actionText: { color: colors.onSurface, fontSize: 16, fontWeight: "600" as const },
    status: { color: colors.onSurfaceSecondary, fontSize: 14, fontWeight: "600" as const },

    backButton: {
      width:
        touch.minimum,
      height:
        touch.minimum,
      alignItems:
        "center",
      justifyContent:
        "center",
      borderRadius: 999,
      backgroundColor:
        colors.glassSoft,
      borderWidth: 1,
      borderColor:
        colors.glassBorder,
    },
  }),
);
