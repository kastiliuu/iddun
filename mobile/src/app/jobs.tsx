import React, {
  useCallback,
  useState,
} from "react";

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
  useRouter,
} from "expo-router";

import {
  getJobs,
  type JobPost,
} from "@/api/jobs";

import {
  EmptyState,
} from "@/components/EmptyState";

import {
  Icon,
} from "@/components/Icon";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function JobsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [items, setItems] =
    useState<JobPost[]>([]);
  const [query, setQuery] =
    useState("");
  const [city, setCity] =
    useState("");
  const [loading, setLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);

  const load = useCallback(
    async () => {
      setLoading(true);

      try {
        const response =
          await getJobs({
            query,
            city,
            limit: 30,
          });

        setItems(
          response.items,
        );
        setError(null);
      } catch (requestError) {
        setItems([]);
        setError(
          requestError
            instanceof Error
            ? requestError.message
            : "Não foi possível carregar as vagas.",
        );
      } finally {
        setLoading(false);
      }
    },
    [city, query],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  return (
    <View style={styles.container}>
      <ScrollView
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
            Vagas
          </Text>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Minhas candidaturas"
            onPress={() =>
              router.push(
                "/job-applications",
              )
            }
            style={styles.headerButton}
          >
            <Icon
              name="bookmark"
              size={18}
              color={colors.onSurface}
            />
          </Pressable>
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>
            OPORTUNIDADES
          </Text>

          <Text style={styles.title}>
            Encontre seu próximo espaço.
          </Text>

          <Text style={styles.description}>
            Vagas publicadas por estabelecimentos da rede IDDUN.
          </Text>
        </View>

        <View style={styles.filters}>
          <View style={styles.inputWrap}>
            <Icon
              name="search"
              size={17}
              color={colors.muted}
            />

            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="Cargo ou especialidade"
              placeholderTextColor={colors.muted}
              style={styles.input}
              returnKeyType="search"
              onSubmitEditing={() => {
                void load();
              }}
            />
          </View>

          <View style={styles.inputWrap}>
            <Icon
              name="map-pin"
              size={17}
              color={colors.muted}
            />

            <TextInput
              value={city}
              onChangeText={setCity}
              placeholder="Cidade (opcional)"
              placeholderTextColor={colors.muted}
              style={styles.input}
              returnKeyType="search"
              onSubmitEditing={() => {
                void load();
              }}
            />
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Buscar vagas"
            onPress={() => {
              void load();
            }}
            style={styles.searchButton}
          >
            <Text style={styles.searchButtonText}>
              Buscar
            </Text>
          </Pressable>
        </View>

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
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="Nenhuma vaga encontrada"
            description="Tente ajustar a busca ou remover o filtro de cidade."
          />
        ) : (
          <View style={styles.list}>
            {items.map((job) => (
              <Pressable
                key={job.id}
                accessibilityRole="button"
                accessibilityLabel={
                  `${job.title} em ${job.establishment.name}`
                }
                onPress={() =>
                  router.push(
                    `/job/${job.id}`,
                  )
                }
                style={({ pressed }) => [
                  styles.card,
                  pressed &&
                    styles.pressed,
                ]}
              >
                <View style={styles.cardTop}>
                  <View style={styles.iconWrap}>
                    <Icon
                      name="briefcase"
                      size={18}
                      color={colors.plum}
                    />
                  </View>

                  <View style={styles.cardCopy}>
                    <Text style={styles.cardTitle}>
                      {job.title}
                    </Text>

                    <Text style={styles.cardBusiness}>
                      {job.establishment.name}
                    </Text>
                  </View>

                  <Icon
                    name="chevron-right"
                    size={18}
                    color={colors.muted}
                  />
                </View>

                <View style={styles.metaRow}>
                  {job.specialty ? (
                    <View style={styles.metaPill}>
                      <Text style={styles.metaText}>
                        {job.specialty}
                      </Text>
                    </View>
                  ) : null}

                  {job.city ? (
                    <View style={styles.metaPill}>
                      <Text style={styles.metaText}>
                        {job.city}
                        {job.state
                          ? ` · ${job.state}`
                          : ""}
                      </Text>
                    </View>
                  ) : null}
                </View>

                {job.compensationText ? (
                  <Text style={styles.compensation}>
                    {job.compensationText}
                  </Text>
                ) : null}
              </Pressable>
            ))}
          </View>
        )}

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

    hero: {
      marginTop: spacing.xl,
    },

    eyebrow: {
      color: colors.plum,
      fontFamily: fonts.sansMedium,
      fontSize: 10,
      letterSpacing: 1.4,
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

    filters: {
      marginTop: spacing.xl,
      gap: spacing.sm,
    },

    inputWrap: {
      minHeight: 50,
      paddingHorizontal: spacing.md,
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.sm,
      borderRadius: radius.md,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    input: {
      flex: 1,
      minWidth: 0,
      color: colors.onSurface,
      fontFamily: fonts.sans,
      fontSize: 13,
    },

    searchButton: {
      minHeight: touch.minimum,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: radius.pill,
      backgroundColor: colors.plumSoftStrong,
      borderWidth: 1,
      borderColor: colors.borderStrong,
    },

    searchButtonText: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 13,
    },

    loading: {
      minHeight: 240,
      alignItems: "center",
      justifyContent: "center",
    },

    list: {
      marginTop: spacing.xl,
      gap: spacing.md,
    },

    card: {
      padding: spacing.lg,
      borderRadius: radius.lg,
      backgroundColor: colors.surfaceSecondary,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    cardTop: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
    },

    iconWrap: {
      width: 42,
      height: 42,
      borderRadius: radius.pill,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.plumSoft,
    },

    cardCopy: {
      flex: 1,
      minWidth: 0,
    },

    cardTitle: {
      color: colors.onSurface,
      fontFamily: fonts.sansSemiBold,
      fontSize: 15,
    },

    cardBusiness: {
      marginTop: 3,
      color: colors.muted,
      fontFamily: fonts.sans,
      fontSize: 12,
    },

    metaRow: {
      marginTop: spacing.md,
      flexDirection: "row",
      flexWrap: "wrap",
      gap: spacing.sm,
    },

    metaPill: {
      paddingHorizontal: spacing.md,
      paddingVertical: 6,
      borderRadius: radius.pill,
      backgroundColor: colors.glassSoft,
    },

    metaText: {
      color: colors.onSurfaceSecondary,
      fontFamily: fonts.sans,
      fontSize: 11,
    },

    compensation: {
      marginTop: spacing.md,
      color: colors.plum,
      fontFamily: fonts.sansMedium,
      fontSize: 12,
    },

    pressed: {
      opacity: 0.8,
    },

    bottomSpace: {
      height: 80,
    },
  }),
);
