/**
 * Central de notificações no app (PR 6b; DEC-ID-215–223; D-SOC-22 e 24).
 *
 * Mesmas abas da Web: Todas, Reservas, Social e Profissional e Empresa,
 * com contagens reais e o filtro "Só não lidas". Abrir um aviso marca como
 * lido e o servidor devolve o destino só se o acesso ainda vale; aviso de
 * outro contexto mostra o nome dele e "Abrir como X". Marcar todas é ação
 * explícita. Reservas são essenciais e não se desligam.
 */
import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  Switch,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import {
  useFocusEffect,
  useRouter,
} from "expo-router";

import { API_URL } from "@/api/client";
import { EmptyState } from "@/components/EmptyState";
import { Icon, type IconName } from "@/components/Icon";
import { useToast } from "@/components/Toast";

import {
  getNotificationPreferences,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  openNotification,
  updateNotificationPreferences,
  type NotificationCounts,
  type NotificationItem,
  type NotificationPreferences,
  type NotificationTarget,
} from "@/api/notifications";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  typography,
  useTheme,
} from "@/theme";

const PAGE = 20;

type Tab = "all" | "bookings" | "social" | "work";

const TABS: { id: Tab; label: string }[] = [
  { id: "all", label: "Todas" },
  { id: "bookings", label: "Reservas" },
  { id: "social", label: "Social" },
  { id: "work", label: "Profissional e Empresa" },
];

const KIND_ICONS: Record<string, IconName> = {
  booking: "calendar",
  iddun_now: "clock",
  follow: "user-plus",
  like: "heart",
  comment: "message-circle",
  membership: "briefcase",
  review: "star",
  system: "info",
};

function formatNotificationTime(createdAt: string) {
  const timestamp = new Date(createdAt).getTime();
  const minutes = Math.max(1, Math.floor((Date.now() - timestamp) / 60_000));

  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
  }).format(new Date(timestamp));
}

function isOtherContext(notification: NotificationItem) {
  return (
    (notification.contextType === "professional" ||
      notification.contextType === "establishment") &&
    Boolean(notification.contextLabel)
  );
}

export default function NotificationsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const [tab, setTab] = useState<Tab>("all");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [counts, setCounts] = useState<NotificationCounts | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [savingPreference, setSavingPreference] = useState(false);

  // Evita que uma resposta antiga sobrescreva a aba atual.
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);

    try {
      const response = await getNotifications({
        limit: PAGE,
        unreadOnly,
        category: tab === "all" ? undefined : tab,
      });
      if (current !== requestId.current) return;

      setItems(response.items);
      setCounts(response.counts ?? null);
      setUnreadCount(response.unreadCount);
      setNextOffset(response.pagination.nextOffset);
      setError(null);
    } catch (requestError) {
      if (current !== requestId.current) return;
      setItems([]);
      setCounts(null);
      setNextOffset(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar suas notificações.",
      );
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }, [tab, unreadOnly]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  useEffect(() => {
    getNotificationPreferences()
      .then((response) => setPreferences(response.preferences))
      .catch(() => setPreferences(null));
  }, []);

  const loadMore = async () => {
    if (nextOffset === null || loadingMore) return;
    setLoadingMore(true);
    try {
      const response = await getNotifications({
        offset: nextOffset,
        limit: PAGE,
        unreadOnly,
        category: tab === "all" ? undefined : tab,
      });
      setItems((current) => [...current, ...response.items]);
      setNextOffset(response.pagination.nextOffset);
    } catch {
      toast.show({
        title: "Não foi possível carregar mais avisos.",
        icon: "alert-circle",
      });
    } finally {
      setLoadingMore(false);
    }
  };

  const markLocallyRead = (notification: NotificationItem) => {
    if (notification.read) return;
    setUnreadCount((value) => Math.max(0, value - 1));
    if (unreadOnly) {
      // No filtro "Só não lidas", o aviso lido sai da lista e da contagem.
      setItems((current) => current.filter((item) => item.id !== notification.id));
      setCounts((current) => {
        if (!current) return current;
        const key = notification.category as keyof NotificationCounts | undefined;
        return {
          ...current,
          all: Math.max(0, current.all - 1),
          ...(key && key in current ? { [key]: Math.max(0, current[key] - 1) } : {}),
        };
      });
    } else {
      setItems((current) =>
        current.map((item) =>
          item.id === notification.id
            ? { ...item, read: true, readAt: item.readAt ?? new Date().toISOString() }
            : item,
        ),
      );
    }
  };

  const goTo = (target: NotificationTarget) => {
    const id = target.id ?? "";
    switch (target.type) {
      case "booking":
      case "review_booking":
        router.push({ pathname: "/booking-detail", params: { id } });
        return;
      case "experience":
        router.push({ pathname: "/service/[id]", params: { id } });
        return;
      case "post":
        router.push({ pathname: "/post/[id]", params: { id } });
        return;
      case "professional":
        router.push({ pathname: "/professional/[id]", params: { id } });
        return;
      case "establishment":
        router.push({ pathname: "/establishment/[id]", params: { id } });
        return;
      case "membership":
        router.push("/team-invitations");
        return;
      case "business_team":
        router.push({ pathname: "/establishment-team/[id]", params: { id } });
        return;
      default:
        // Agenda do Pro e demais telas ainda só na Web: abre o site.
        void Linking.openURL(`${API_URL}${target.webPath}`);
    }
  };

  const handleOpen = async (notification: NotificationItem) => {
    if (opening) return;
    setOpening(notification.id);
    try {
      const response = await openNotification(notification.id);
      markLocallyRead(notification);
      if (response.target) {
        goTo(response.target);
      } else {
        toast.show({
          title: "Este aviso não leva a um conteúdo disponível para você agora.",
          icon: "info",
        });
      }
    } catch {
      toast.show({
        title: "Não foi possível abrir este aviso.",
        body: "Tente novamente em instantes.",
        icon: "alert-circle",
      });
    } finally {
      setOpening(null);
    }
  };

  const handleMarkOne = async (notification: NotificationItem) => {
    try {
      await markNotificationRead(notification.id);
      markLocallyRead(notification);
    } catch {
      toast.show({ title: "Não foi possível marcar como lida.", icon: "alert-circle" });
    }
  };

  const handleMarkAll = async () => {
    try {
      await markAllNotificationsRead();
      setUnreadCount(0);
      if (unreadOnly) {
        void load();
      } else {
        setItems((current) =>
          current.map((item) => ({
            ...item,
            read: true,
            readAt: item.readAt ?? new Date().toISOString(),
          })),
        );
      }
      toast.show({ title: "Todas as notificações foram marcadas como lidas.", icon: "check" });
    } catch {
      toast.show({ title: "Não foi possível marcar todas como lidas.", icon: "alert-circle" });
    }
  };

  const savePreference = async (key: "socialEnabled" | "workEnabled", value: boolean) => {
    if (!preferences || savingPreference) return;
    const previous = preferences;
    setPreferences({ ...preferences, [key]: value });
    setSavingPreference(true);
    try {
      const response = await updateNotificationPreferences({ [key]: value });
      setPreferences(response.preferences);
    } catch {
      setPreferences(previous);
      toast.show({ title: "Não foi possível salvar a preferência.", icon: "alert-circle" });
    } finally {
      setSavingPreference(false);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => {
              if (router.canGoBack()) router.back();
              else router.replace("/(tabs)");
            }}
            style={({ pressed }) => [styles.headerButton, pressed && styles.pressed]}
          >
            <Icon name="arrow-left" size={20} color={colors.onSurface} />
          </Pressable>

          <Image
            source={require("../../assets/branding/iddun-logo-white.png")}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

          <View style={styles.headerButtonPlaceholder} />
        </View>

        <View style={styles.titleRow}>
          <View style={styles.titleArea}>
            <Text style={styles.eyebrow}>SUA ATIVIDADE</Text>
            <Text style={styles.title} accessibilityRole="header">
              Notificações
            </Text>
            <Text style={styles.subtitle}>
              {unreadCount === 0
                ? "Nada novo por enquanto."
                : unreadCount === 1
                  ? "1 não lida"
                  : `${unreadCount} não lidas`}
            </Text>
          </View>

          {unreadCount > 0 ? (
            <Pressable
              accessibilityRole="button"
              onPress={() => void handleMarkAll()}
              style={({ pressed }) => [styles.markAllButton, pressed && styles.pressed]}
            >
              <Text style={styles.markAllText}>Marcar todas como lidas</Text>
            </Pressable>
          ) : null}
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.tabs}
          style={styles.tabsScroll}
          accessibilityRole="tablist"
        >
          {TABS.map((item) => {
            const selected = tab === item.id;
            const count = counts ? counts[item.id] : null;
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

        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: unreadOnly }}
          onPress={() => setUnreadOnly((value) => !value)}
          style={[styles.filter, unreadOnly && styles.tabSelected]}
        >
          {unreadOnly ? <Icon name="check" size={14} color={colors.surface} /> : null}
          <Text style={[styles.tabText, unreadOnly && styles.tabTextSelected]}>Só não lidas</Text>
        </Pressable>

        {loading ? (
          <View style={styles.loadingState}>
            <ActivityIndicator color={colors.plum} />
          </View>
        ) : error ? (
          <EmptyState
            title="Notificações indisponíveis"
            description={error}
            actionLabel="Tentar novamente"
            onActionPress={() => void load()}
          />
        ) : items.length > 0 ? (
          <View style={styles.list}>
            {items.map((notification) => {
              const otherContext = isOtherContext(notification);
              return (
                <View
                  key={notification.id}
                  style={[styles.card, !notification.read && styles.cardUnread]}
                >
                  <View style={styles.iconWrap}>
                    <Icon
                      name={KIND_ICONS[notification.kind] ?? "bell"}
                      size={18}
                      color={notification.read ? colors.muted : colors.plum}
                    />
                  </View>

                  <View style={styles.cardContent}>
                    <Pressable
                      accessibilityRole="link"
                      accessibilityLabel={`${notification.read ? "" : "Não lida: "}${notification.title}. ${notification.body}`}
                      accessibilityState={{ busy: opening === notification.id }}
                      onPress={() => void handleOpen(notification)}
                      style={({ pressed }) => [styles.cardLink, pressed && styles.pressed]}
                    >
                      <Text
                        style={[styles.cardTitle, !notification.read && styles.cardTitleUnread]}
                        numberOfLines={2}
                      >
                        {notification.title}
                      </Text>
                      <Text style={styles.cardBody} numberOfLines={3}>
                        {notification.body}
                      </Text>
                    </Pressable>

                    <View style={styles.meta}>
                      <Text style={styles.metaText}>{formatNotificationTime(notification.createdAt)}</Text>
                      {notification.contextLabel ? (
                        <Text style={styles.contextChip}>{notification.contextLabel}</Text>
                      ) : null}
                    </View>

                    {otherContext ? (
                      // DEC-ID-221: troca de contexto explícita, nunca silenciosa.
                      <Pressable
                        accessibilityRole="link"
                        onPress={() => void handleOpen(notification)}
                        style={({ pressed }) => [styles.switchLink, pressed && styles.pressed]}
                      >
                        <Text style={styles.switchText}>Abrir como {notification.contextLabel}</Text>
                        <Icon name="chevron-right" size={14} color={colors.onSurface} />
                      </Pressable>
                    ) : null}
                  </View>

                  {!notification.read ? (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`Marcar como lida: ${notification.title}`}
                      onPress={() => void handleMarkOne(notification)}
                      style={({ pressed }) => [styles.readButton, pressed && styles.pressed]}
                    >
                      <Icon name="check" size={16} color={colors.onSurface} />
                    </Pressable>
                  ) : null}
                </View>
              );
            })}

            {nextOffset !== null ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void loadMore()}
                disabled={loadingMore}
                style={({ pressed }) => [styles.moreButton, pressed && styles.pressed]}
              >
                {loadingMore ? (
                  <ActivityIndicator color={colors.onSurface} />
                ) : (
                  <Text style={styles.tabText}>Ver mais</Text>
                )}
              </Pressable>
            ) : null}
          </View>
        ) : (
          <EmptyState
            title={unreadOnly ? "Nenhuma notificação não lida aqui." : "Nada por aqui ainda."}
            description="Reservas, novos seguidores, curtidas, comentários e convites aparecem aqui quando acontecem."
          />
        )}

        <View style={styles.preferences}>
          <Text style={styles.preferencesTitle} accessibilityRole="header">
            Preferências
          </Text>

          <View style={styles.preferenceRow}>
            <View style={styles.preferenceText}>
              <Text style={styles.preferenceLabel}>Reservas</Text>
              <Text style={styles.preferenceHint}>
                Sempre ativas: confirmações, cancelamentos e pedidos são essenciais. Também chegam por e-mail.
              </Text>
            </View>
            <View style={styles.fixed}>
              <Icon name="check" size={14} color={colors.onSurface} />
              <Text style={styles.fixedText}>Ativas</Text>
            </View>
          </View>

          {preferences ? (
            <>
              <View style={styles.preferenceRow}>
                <View style={styles.preferenceText}>
                  <Text style={styles.preferenceLabel}>Social</Text>
                  <Text style={styles.preferenceHint}>Novos seguidores, curtidas e comentários.</Text>
                </View>
                <Switch
                  value={preferences.socialEnabled}
                  onValueChange={(value) => void savePreference("socialEnabled", value)}
                  disabled={savingPreference}
                  accessibilityLabel="Avisos sociais"
                />
              </View>

              <View style={styles.preferenceRow}>
                <View style={styles.preferenceText}>
                  <Text style={styles.preferenceLabel}>Profissional e Empresa</Text>
                  <Text style={styles.preferenceHint}>Convites de vínculo e avaliações recebidas.</Text>
                </View>
                <Switch
                  value={preferences.workEnabled}
                  onValueChange={(value) => void savePreference("workEnabled", value)}
                  disabled={savingPreference}
                  accessibilityLabel="Avisos de Profissional e Empresa"
                />
              </View>
            </>
          ) : (
            <Text style={styles.preferenceHint}>Não foi possível carregar suas preferências agora.</Text>
          )}
        </View>

        <View style={styles.bottomSpace} />
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
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
  logo: {
    width: 104,
    height: 32,
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
  headerButtonPlaceholder: {
    width: touch.minimum,
    height: touch.minimum,
  },
  titleRow: {
    marginTop: spacing.xl,
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  titleArea: {
    flex: 1,
    minWidth: 180,
  },
  eyebrow: {
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: typography.small,
    letterSpacing: 1.4,
  },
  title: {
    marginTop: spacing.sm,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: typography.editorial,
    lineHeight: 38,
    letterSpacing: -0.4,
  },
  subtitle: {
    marginTop: spacing.sm,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.bodySmall,
  },
  markAllButton: {
    minHeight: touch.minimum,
    justifyContent: "center",
  },
  markAllText: {
    color: colors.plum,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
  },
  tabsScroll: {
    marginTop: spacing.xl,
    marginHorizontal: -spacing.lg,
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
  filter: {
    marginTop: spacing.md,
    alignSelf: "flex-start",
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
  loadingState: {
    minHeight: 180,
    alignItems: "center",
    justifyContent: "center",
  },
  list: {
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  card: {
    padding: spacing.md,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  cardUnread: {
    borderColor: colors.plum,
    borderLeftWidth: 4,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surfaceTertiary,
    flexShrink: 0,
  },
  cardContent: {
    flex: 1,
    minWidth: 0,
    gap: spacing.xs,
  },
  cardLink: {
    gap: spacing.xs,
  },
  cardTitle: {
    color: colors.onSurface,
    fontFamily: fonts.sansMedium,
    fontSize: typography.body,
  },
  cardTitleUnread: {
    fontFamily: fonts.sansSemiBold,
  },
  cardBody: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.bodySmall,
    lineHeight: 18,
  },
  meta: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: spacing.sm,
  },
  metaText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.small,
  },
  contextChip: {
    paddingHorizontal: spacing.sm,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.small,
  },
  switchLink: {
    minHeight: touch.minimum,
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  switchText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
  },
  readButton: {
    width: touch.minimum,
    height: touch.minimum,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.border,
    flexShrink: 0,
  },
  moreButton: {
    marginTop: spacing.sm,
    minHeight: touch.minimum,
    alignSelf: "center",
    paddingHorizontal: spacing.xl,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
  },
  preferences: {
    marginTop: spacing.xl,
    padding: spacing.lg,
    gap: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surfaceSecondary,
  },
  preferencesTitle: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodyLarge,
  },
  preferenceRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  preferenceText: {
    flex: 1,
    minWidth: 0,
    gap: spacing.xs,
  },
  preferenceLabel: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.body,
  },
  preferenceHint: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.small,
    lineHeight: 17,
  },
  fixed: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  fixedText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
  },
  bottomSpace: {
    height: 72,
  },
  pressed: {
    opacity: 0.76,
  },
}));
