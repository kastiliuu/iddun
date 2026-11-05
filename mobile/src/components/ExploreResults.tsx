import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import {
  globalSearch,
  type GlobalSearchCounts,
  type GlobalSearchItem,
  type GlobalSearchKind,
  type GlobalSearchResponse,
  type GlobalSearchSort,
} from "@/api/search";
import { CategoryChip } from "@/components/CategoryChip";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  typography,
  useTheme,
} from "@/theme";

/**
 * Resultados do Explorar no app (PR 5b; D-SOC-18, DEC-ID-179–187): o mesmo
 * modelo da Web, com a API de /api/v1/search. Abas por tipo com contagem
 * real, "Ver mais" por tipo, filtros de serviço (preço, horário disponível,
 * ordenação) e estado sem resultados sem nada inventado.
 */

type Tab = "all" | GlobalSearchKind;

const TABS: { id: Tab; label: string; countKey: keyof GlobalSearchCounts }[] = [
  { id: "all", label: "Todos", countKey: "total" },
  { id: "experience", label: "Serviços", countKey: "experiences" },
  { id: "professional", label: "Profissionais", countKey: "professionals" },
  { id: "establishment", label: "Estabelecimentos", countKey: "establishments" },
  { id: "post", label: "Publicações", countKey: "posts" },
];

const SECTIONS: { kind: GlobalSearchKind; key: keyof GlobalSearchResponse["sections"]; title: string }[] = [
  { kind: "experience", key: "experiences", title: "Serviços" },
  { kind: "professional", key: "professionals", title: "Profissionais" },
  { kind: "establishment", key: "establishments", title: "Estabelecimentos" },
  { kind: "post", key: "posts", title: "Publicações" },
];

const SORTS: { id: GlobalSearchSort; label: string }[] = [
  { id: "recommended", label: "Relevância" },
  { id: "lowest_price", label: "Menor preço" },
  { id: "highest_rating", label: "Melhor avaliação" },
  { id: "newest", label: "Mais recentes" },
];

const KIND_LABELS: Record<GlobalSearchKind, string> = {
  experience: "Serviço",
  professional: "Profissional",
  establishment: "Estabelecimento",
  post: "Publicação",
};

const PREVIEW = 4;
const PAGE = 12;

function parsePrice(value: string) {
  const parsed = Number(value.replace(",", "."));
  return value.trim() && Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export type ExploreCategory = { label: string; code?: string };

type Props = {
  query: string;
  category?: string;
  location: string;
  categories: ExploreCategory[];
  onSelectCategory: (label: string) => void;
  onClearFilters: () => void;
};

export function ExploreResults({
  query,
  category,
  location,
  categories,
  onSelectCategory,
  onClearFilters,
}: Props) {
  const styles = useStyles();
  const { colors } = useTheme();

  const [tab, setTab] = useState<Tab>("all");
  const [available, setAvailable] = useState(false);
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [sort, setSort] = useState<GlobalSearchSort>("recommended");
  const [moreFilters, setMoreFilters] = useState(false);

  const [result, setResult] = useState<GlobalSearchResponse | null>(null);
  const [items, setItems] = useState<GlobalSearchItem[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [suggestions, setSuggestions] = useState<{ label: string; count: number }[]>([]);

  const serviceFilters = {
    priceMin: parsePrice(priceMin),
    priceMax: parsePrice(priceMax),
    available,
    sort,
  };
  const hasServiceFilters =
    serviceFilters.priceMin !== undefined
    || serviceFilters.priceMax !== undefined
    || available
    || sort !== "recommended";
  const filterKey = `${priceMin}|${priceMax}|${available}|${sort}`;

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError(false);
      setSuggestions([]);
      globalSearch(
        {
          query,
          category,
          location,
          type: tab === "all" ? undefined : tab,
          limit: tab === "all" ? PREVIEW : PAGE,
          ...serviceFilters,
        },
        controller.signal,
      )
        .then(async (response) => {
          if (controller.signal.aborted) return;
          setResult(response);
          if (tab !== "all") {
            const key = SECTIONS.find((section) => section.kind === tab)?.key ?? "experiences";
            setItems(response.sections[key]);
            setNextOffset(response.page?.nextOffset ?? null);
          }
          // DEC-ID-186: sem resultados, só categorias que têm resultado
          // de verdade para a mesma busca.
          if ((response.counts?.total ?? 0) === 0) {
            const found = await Promise.all(
              categories
                .filter((item) => item.code)
                .map(async (item) => {
                  try {
                    const counts = await globalSearch(
                      { query, category: item.code, limit: 1 },
                      controller.signal,
                    );
                    return { label: item.label, count: counts.counts?.total ?? 0 };
                  } catch {
                    return { label: item.label, count: 0 };
                  }
                }),
            );
            if (!controller.signal.aborted) {
              setSuggestions(found.filter((item) => item.count > 0));
            }
          }
        })
        .catch((reason: unknown) => {
          if (reason instanceof Error && reason.name === "AbortError") return;
          if (controller.signal.aborted) return;
          setError(true);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // serviceFilters muda junto com filterKey.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, category, location, tab, filterKey, retry, categories]);

  const loadMore = async () => {
    if (nextOffset === null || loadingMore || tab === "all") return;
    setLoadingMore(true);
    try {
      const response = await globalSearch({
        query,
        category,
        location,
        type: tab,
        limit: PAGE,
        offset: nextOffset,
        ...serviceFilters,
      });
      const key = SECTIONS.find((section) => section.kind === tab)?.key ?? "experiences";
      setItems((current) => [...current, ...response.sections[key]]);
      setNextOffset(response.page?.nextOffset ?? null);
    } catch {
      setNextOffset(null);
    } finally {
      setLoadingMore(false);
    }
  };

  const clearAll = () => {
    setAvailable(false);
    setPriceMin("");
    setPriceMax("");
    setSort("recommended");
    onClearFilters();
  };

  const counts = result?.counts;
  const filtersActive = hasServiceFilters || Boolean(category) || Boolean(location.trim());

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.tabs}
        accessibilityRole="tablist"
      >
        {TABS.map((item) => {
          const selected = tab === item.id;
          const count = counts ? counts[item.countKey] : null;
          return (
            <Pressable
              key={item.id}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              accessibilityLabel={count === null ? item.label : `${item.label}, ${count}`}
              onPress={() => setTab(item.id)}
              style={[styles.tab, selected && styles.tabSelected]}
            >
              <Text style={[styles.tabText, selected && styles.tabTextSelected]}>{item.label}</Text>
              {count !== null ? (
                <Text style={[styles.tabCount, selected && styles.tabTextSelected]}>{count}</Text>
              ) : null}
            </Pressable>
          );
        })}
      </ScrollView>

      <View style={styles.filters}>
        <Text style={styles.filtersLabel}>Serviços</Text>
        <View style={styles.filterRow}>
          <CategoryChip
            label="Com horário disponível"
            selected={available}
            onPress={() => setAvailable((value) => !value)}
          />
          <TextInput
            value={priceMin}
            onChangeText={setPriceMin}
            placeholder="Preço mín."
            placeholderTextColor={colors.muted}
            keyboardType="decimal-pad"
            accessibilityLabel="Preço mínimo do serviço, em reais"
            style={styles.priceInput}
          />
          <TextInput
            value={priceMax}
            onChangeText={setPriceMax}
            placeholder="Preço máx."
            placeholderTextColor={colors.muted}
            keyboardType="decimal-pad"
            accessibilityLabel="Preço máximo do serviço, em reais"
            style={styles.priceInput}
          />
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ expanded: moreFilters }}
          onPress={() => setMoreFilters((value) => !value)}
          style={styles.moreButton}
        >
          <Text style={styles.moreText}>Mais filtros</Text>
          <Icon name={moreFilters ? "chevron-up" : "chevron-down"} size={16} color={colors.onSurface} />
        </Pressable>
        {moreFilters ? (
          <View style={styles.filterRow} accessibilityLabel="Ordenar serviços por">
            {SORTS.map((item) => (
              <CategoryChip
                key={item.id}
                label={item.label}
                selected={sort === item.id}
                onPress={() => setSort(item.id)}
              />
            ))}
          </View>
        ) : null}
        {hasServiceFilters && tab !== "all" && tab !== "experience" ? (
          <Text style={styles.note}>Preço e horário disponível valem só para serviços.</Text>
        ) : null}
      </View>

      {loading ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.plum} />
        </View>
      ) : error ? (
        <EmptyState
          title="Não foi possível carregar a busca"
          description="Confira sua conexão e tente novamente. Seus filtros foram preservados."
          actionLabel="Tentar novamente"
          onActionPress={() => setRetry((value) => value + 1)}
        />
      ) : (counts?.total ?? 0) === 0 ? (
        <View style={styles.empty}>
          <EmptyState
            title="Nada encontrado com esta busca."
            description={
              filtersActive
                ? "Os filtros podem estar restringindo demais. Tente limpar os filtros."
                : "Tente outras palavras."
            }
            actionLabel={filtersActive ? "Limpar filtros" : undefined}
            onActionPress={filtersActive ? clearAll : undefined}
          />
          {suggestions.length > 0 ? (
            <View style={styles.suggestions}>
              <Text style={styles.note}>{`Categorias com resultados para “${query}”:`}</Text>
              <View style={styles.filterRow}>
                {suggestions.map((item) => (
                  <CategoryChip
                    key={item.label}
                    label={`${item.label} · ${item.count}`}
                    onPress={() => {
                      clearAll();
                      onSelectCategory(item.label);
                    }}
                  />
                ))}
              </View>
            </View>
          ) : null}
        </View>
      ) : tab === "all" ? (
        SECTIONS.filter((section) => (result?.sections[section.key] ?? []).length > 0).map((section) => (
          <View key={section.key} style={styles.section}>
            <View style={styles.sectionHead}>
              <Text style={styles.sectionTitle} accessibilityRole="header">
                {section.title} <Text style={styles.sectionCount}>{counts?.[section.key] ?? 0}</Text>
              </Text>
              {(counts?.[section.key] ?? 0) > (result?.sections[section.key] ?? []).length ? (
                <Pressable accessibilityRole="button" onPress={() => setTab(section.kind)} style={styles.seeAll}>
                  <Text style={styles.seeAllText}>{section.kind === "post" ? "Ver todas" : "Ver todos"}</Text>
                </Pressable>
              ) : null}
            </View>
            {(result?.sections[section.key] ?? []).map((item) => (
              <ResultRow key={`${item.kind}-${item.id}`} item={item} />
            ))}
          </View>
        ))
      ) : (
        <View style={styles.section}>
          {items.map((item) => (
            <ResultRow key={`${item.kind}-${item.id}`} item={item} />
          ))}
          {items.length === 0 ? (
            <EmptyState
              title="Nenhum resultado deste tipo"
              description="Veja os outros tipos de resultado."
              actionLabel="Ver todos os tipos"
              onActionPress={() => setTab("all")}
              compact
            />
          ) : null}
          {nextOffset !== null ? (
            <Pressable
              accessibilityRole="button"
              onPress={() => void loadMore()}
              style={styles.moreResults}
            >
              {loadingMore ? (
                <ActivityIndicator color={colors.plum} />
              ) : (
                <Text style={styles.moreText}>Ver mais</Text>
              )}
            </Pressable>
          ) : null}
        </View>
      )}
    </View>
  );
}

function ResultRow({ item }: { item: GlobalSearchItem }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const open = () => {
    const id = encodeURIComponent(item.routeId);
    if (item.kind === "experience") router.push(`/service/${id}`);
    else if (item.kind === "professional") router.push(`/professional/${id}`);
    else if (item.kind === "establishment") router.push(`/establishment/${id}`);
    else router.push(`/post/${id}`);
  };

  const meta: string[] = [];
  if (item.location && item.kind !== "post") meta.push(item.location);
  if (item.reviewsCount > 0) meta.push(`★ ${item.rating.toFixed(1).replace(".", ",")} (${item.reviewsCount})`);
  if (item.kind === "experience" && item.price) {
    meta.push(
      new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(item.price),
    );
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${KIND_LABELS[item.kind]}: ${item.title}`}
      onPress={open}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <View style={[styles.media, item.kind === "professional" && styles.mediaRound]}>
        {item.image ? (
          <Image source={{ uri: item.image }} style={styles.mediaImage} contentFit="cover" />
        ) : (
          <Text style={styles.initials}>{initials(item.title)}</Text>
        )}
      </View>
      <View style={styles.rowBody}>
        <Text style={styles.kind}>{KIND_LABELS[item.kind]}</Text>
        <Text style={styles.rowTitle} numberOfLines={2}>
          {item.title}
        </Text>
        {item.subtitle ? (
          <Text style={styles.rowSubtitle} numberOfLines={2}>
            {item.subtitle}
          </Text>
        ) : null}
        {meta.length ? <Text style={styles.meta}>{meta.join(" · ")}</Text> : null}
        {item.kind === "experience" ? (
          <View style={styles.slot}>
            <Icon name="calendar" size={12} color={item.nextAvailableLabel ? colors.onSurface : colors.muted} />
            {/* DEC-ID-183: só o próximo horário real. */}
            <Text style={item.nextAvailableLabel ? styles.slotText : styles.meta}>
              {item.nextAvailableLabel ?? "Sem horário disponível"}
            </Text>
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    gap: spacing.lg,
  },
  tabs: {
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  tab: {
    minHeight: touch.minimum,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  tabSelected: {
    backgroundColor: colors.onSurface,
    borderColor: colors.onSurface,
  },
  tabText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
  },
  tabCount: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: typography.bodySmall,
  },
  tabTextSelected: {
    color: colors.surface,
  },
  filters: {
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
  },
  filtersLabel: {
    color: colors.muted,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.small,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  priceInput: {
    minHeight: touch.minimum,
    minWidth: 104,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: typography.bodySmall,
  },
  moreButton: {
    alignSelf: "flex-start",
    minHeight: touch.minimum,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  moreText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
  },
  note: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.small,
  },
  loading: {
    paddingVertical: spacing.xl,
  },
  empty: {
    gap: spacing.md,
  },
  suggestions: {
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
  },
  section: {
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
  },
  sectionHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionTitle: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: typography.titleSmall,
  },
  sectionCount: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: typography.bodySmall,
  },
  seeAll: {
    minHeight: touch.minimum,
    justifyContent: "center",
  },
  seeAllText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
    textDecorationLine: "underline",
  },
  row: {
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
  },
  pressed: {
    opacity: 0.8,
  },
  media: {
    width: 72,
    height: 72,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.sm,
    backgroundColor: colors.surfaceTertiary,
  },
  mediaRound: {
    borderRadius: radius.pill,
  },
  mediaImage: {
    width: "100%",
    height: "100%",
  },
  initials: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.body,
  },
  rowBody: {
    flex: 1,
    gap: spacing.xs,
  },
  kind: {
    color: colors.muted,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.small,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  rowTitle: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.body,
  },
  rowSubtitle: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.bodySmall,
  },
  meta: {
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: typography.small,
  },
  slot: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  slotText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.small,
  },
  moreResults: {
    minHeight: touch.minimum,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
  },
}));
