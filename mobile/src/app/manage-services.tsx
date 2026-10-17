import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import {
  useRouter,
} from "expo-router";

import { getManagedServices, type ManagedService } from "@/api/services";

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
  useEffect(() => { void reload(); }, [reload]);

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
                "/(tabs)/create",
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
          actionLabel="Voltar"
          onActionPress={() => router.back()}
        />
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
          <Text style={{ color: colors.onSurface, fontSize: 20, fontWeight: "700" }}>
            Seus serviços ({items.length})
          </Text>
          {items.map(item => (
            <View key={item.id} style={{
              padding: spacing.md,
              borderWidth: 1,
              borderColor: colors.glassBorder,
              borderRadius: 12,
              backgroundColor: colors.glassSoft,
              gap: spacing.xs,
            }}>
              <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 16 }}>{item.title}</Text>
              <Text style={{ color: colors.muted }}>{item.category} · {item.durationMinutes} min · R$ {item.price.toFixed(2).replace(".", ",")}</Text>
              <Text style={{ color: colors.plum }}>
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

    header: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
    },

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
