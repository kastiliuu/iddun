import React, {
  useMemo,
} from "react";
import {
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";

import {
  getProfessionalById,
} from "@/mocks/data";

import {
  Notification,
  store,
  useStoreVersion,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

function formatNotificationTime(
  timestamp: number,
) {
  const diff =
    Date.now() - timestamp;

  const minutes = Math.max(
    1,
    Math.floor(
      diff / 60_000,
    ),
  );

  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(
    minutes / 60,
  );

  if (hours < 24) {
    return `${hours}h`;
  }

  const days = Math.floor(
    hours / 24,
  );

  if (days < 7) {
    return `${days}d`;
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day: "2-digit",
      month: "short",
    },
  ).format(
    new Date(timestamp),
  );
}

function getNotificationIcon(
  notification: Notification,
) {
  switch (notification.kind) {
    case "iddun_now":
      return "clock";

    case "follow_back":
      return "user-plus";

    case "system":
    default:
      return "bell";
  }
}

export default function NotificationsScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const notifications =
    store.getNotifications();

  const unreadCount =
    store.unreadCount();

  const sortedNotifications =
    useMemo(() => {
      return [...notifications].sort(
        (a, b) =>
          b.createdAt -
          a.createdAt,
      );
    }, [notifications]);

  const handleNotificationPress = (
    notification: Notification,
  ) => {
    if (!notification.read) {
      store.markRead(
        notification.id,
      );
    }

    if (
      notification.kind ===
        "iddun_now" &&
      notification.serviceId
    ) {
      router.push(
        `/service/${notification.serviceId}`,
      );

      return;
    }

    if (
      notification.authorId
    ) {
      const profile =
        getProfessionalById(
          notification.authorId,
        );

      if (!profile) {
        return;
      }

      router.push(
        profile.kind ===
          "establishment"
          ? `/establishment/${profile.id}`
          : `/professional/${profile.id}`,
      );
    }
  };

  return (
    <View
      style={
        styles.container
      }
    >
      <ScrollView
        contentContainerStyle={
          styles.content
        }
        showsVerticalScrollIndicator={
          false
        }
      >
        <View
          style={
            styles.header
          }
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => {
              if (
                router.canGoBack()
              ) {
                router.back();
              } else {
                router.replace(
                  "/(tabs)",
                );
              }
            }}
            style={({
              pressed,
            }) => [
              styles.headerButton,
              pressed &&
                styles.pressed,
            ]}
          >
            <Icon
              name="arrow-left"
              size={20}
              color={
                colors.onSurface
              }
            />
          </Pressable>

          <Image
            source={require(
              "../../assets/branding/iddun-logo-white.png",
            )}
            style={
              styles.logo
            }
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

          <View
            style={
              styles.headerButtonPlaceholder
            }
          />
        </View>

        <View
          style={
            styles.titleRow
          }
        >
          <View
            style={
              styles.titleArea
            }
          >
            <Text
              style={
                styles.eyebrow
              }
            >
              SUA ATIVIDADE
            </Text>

            <Text
              style={
                styles.title
              }
            >
              Notificações
            </Text>

            <Text
              style={
                styles.subtitle
              }
            >
              {unreadCount === 0
                ? "Você está em dia."
                : unreadCount === 1
                  ? "1 novidade esperando por você."
                  : `${unreadCount} novidades esperando por você.`}
            </Text>
          </View>

          {unreadCount >
          0 ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Marcar todas como lidas"
              onPress={() =>
                store.markAllRead()
              }
              style={({
                pressed,
              }) => [
                styles.markAllButton,
                pressed &&
                  styles.pressed,
              ]}
            >
              <Text
                style={
                  styles.markAllText
                }
              >
                Marcar como lidas
              </Text>
            </Pressable>
          ) : null}
        </View>

        {sortedNotifications.length >
        0 ? (
          <View
            style={
              styles.list
            }
          >
            {sortedNotifications.map(
              (
                notification,
              ) => {
                const profile =
                  notification.authorId
                    ? getProfessionalById(
                        notification.authorId,
                      )
                    : undefined;

                return (
                  <Pressable
                    key={
                      notification.id
                    }
                    accessibilityRole="button"
                    accessibilityLabel={`${notification.title}. ${notification.body}`}
                    onPress={() =>
                      handleNotificationPress(
                        notification,
                      )
                    }
                    style={({
                      pressed,
                    }) => [
                      styles.notificationCard,

                      !notification.read &&
                        styles.notificationUnread,

                      pressed &&
                        styles.pressed,
                    ]}
                  >
                    <View
                      style={
                        styles.iconWrap
                      }
                    >
                      <Icon
                        name={getNotificationIcon(
                          notification,
                        )}
                        size={18}
                        color={
                          notification.read
                            ? colors.muted
                            : colors.plum
                        }
                      />
                    </View>

                    <View
                      style={
                        styles.notificationContent
                      }
                    >
                      <View
                        style={
                          styles.notificationHeader
                        }
                      >
                        <Text
                          style={[
                            styles.notificationTitle,

                            !notification.read &&
                              styles.notificationTitleUnread,
                          ]}
                          numberOfLines={
                            1
                          }
                        >
                          {
                            notification.title
                          }
                        </Text>

                        <Text
                          style={
                            styles.notificationTime
                          }
                        >
                          {formatNotificationTime(
                            notification.createdAt,
                          )}
                        </Text>
                      </View>

                      <Text
                        style={
                          styles.notificationBody
                        }
                        numberOfLines={
                          3
                        }
                      >
                        {
                          notification.body
                        }
                      </Text>

                      {notification.timeLabel ? (
                        <View
                          style={
                            styles.timeBadge
                          }
                        >
                          <Icon
                            name="clock"
                            size={11}
                            color={
                              colors.plum
                            }
                          />

                          <Text
                            style={
                              styles.timeBadgeText
                            }
                          >
                            {
                              notification.timeLabel
                            }
                          </Text>
                        </View>
                      ) : null}

                      {profile ? (
                        <View
                          style={
                            styles.profileHint
                          }
                        >
                          <Text
                            style={
                              styles.profileHintText
                            }
                          >
                            {
                              profile.name
                            }
                          </Text>

                          <Icon
                            name="chevron-right"
                            size={13}
                            color={
                              colors.muted
                            }
                          />
                        </View>
                      ) : null}
                    </View>

                    {!notification.read ? (
                      <View
                        accessibilityLabel="Não lida"
                        style={
                          styles.unreadDot
                        }
                      />
                    ) : null}
                  </Pressable>
                );
              },
            )}
          </View>
        ) : (
          <EmptyState
            title="Tudo tranquilo por aqui"
            description="Quando houver novos horários, interações ou novidades do IDDUN, elas aparecerão aqui."
            actionLabel="Descobrir"
            onActionPress={() =>
              router.push(
                "/(tabs)/discover",
              )
            }
          />
        )}

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>
    </View>
  );
}

const useStyles =
  makeStyles(
    (colors) => ({
      container: {
        flex: 1,
        backgroundColor:
          colors.surface,
      },

      content: {
        paddingTop: 54,
        paddingHorizontal:
          spacing.lg,
      },

      header: {
        minHeight: 52,

        flexDirection:
          "row",

        alignItems:
          "center",

        justifyContent:
          "space-between",
      },

      logo: {
        width: 104,
        height: 32,
      },

      headerButton: {
        width:
          touch.minimum,

        height:
          touch.minimum,

        borderRadius:
          radius.pill,

        alignItems:
          "center",

        justifyContent:
          "center",

        backgroundColor:
          colors.glassSoft,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      headerButtonPlaceholder: {
        width:
          touch.minimum,

        height:
          touch.minimum,
      },

      titleRow: {
        marginTop:
          spacing.xl,

        flexDirection:
          "row",

        alignItems:
          "flex-end",

        justifyContent:
          "space-between",

        gap: spacing.md,
      },

      titleArea: {
        flex: 1,
        minWidth: 0,
      },

      eyebrow: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 10,
        lineHeight: 14,

        letterSpacing: 1.4,
      },

      title: {
        marginTop:
          spacing.sm,

        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 32,
        lineHeight: 38,

        letterSpacing: -0.4,
      },

      subtitle: {
        marginTop:
          spacing.sm,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sans,

        fontSize: 12,
        lineHeight: 18,
      },

      markAllButton: {
        minHeight:
          touch.minimum,

        justifyContent:
          "center",

        paddingLeft:
          spacing.md,
      },

      markAllText: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 11,
        lineHeight: 15,
      },

      list: {
        marginTop:
          spacing.xl,

        gap: spacing.sm,
      },

      notificationCard: {
        minHeight: 104,

        padding:
          spacing.md,

        borderRadius:
          radius.md,

        flexDirection:
          "row",

        alignItems:
          "flex-start",

        gap: spacing.md,

        backgroundColor:
          colors.surfaceSecondary,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      notificationUnread: {
        backgroundColor:
          colors.plumSoft,

        borderColor:
          colors.brandTertiary,
      },

      iconWrap: {
        width: 42,
        height: 42,

        borderRadius:
          radius.md,

        alignItems:
          "center",

        justifyContent:
          "center",

        backgroundColor:
          colors.surfaceTertiary,

        flexShrink: 0,
      },

      notificationContent: {
        flex: 1,
        minWidth: 0,
      },

      notificationHeader: {
        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,
      },

      notificationTitle: {
        flex: 1,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sansMedium,

        fontSize: 13,
        lineHeight: 17,
      },

      notificationTitleUnread: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.sansSemiBold,
      },

      notificationTime: {
        flexShrink: 0,

        color:
          colors.muted,

        fontFamily:
          fonts.sans,

        fontSize: 9,
        lineHeight: 12,
      },

      notificationBody: {
        marginTop:
          spacing.xs,

        color:
          colors.muted,

        fontFamily:
          fonts.sans,

        fontSize: 11,
        lineHeight: 16,
      },

      timeBadge: {
        alignSelf:
          "flex-start",

        marginTop:
          spacing.sm,

        paddingHorizontal:
          spacing.sm,

        paddingVertical: 5,

        borderRadius:
          radius.pill,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.xs,

        backgroundColor:
          colors.glassSoft,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      timeBadgeText: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 10,
        lineHeight: 13,
      },

      profileHint: {
        marginTop:
          spacing.sm,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.xs,
      },

      profileHintText: {
        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sansMedium,

        fontSize: 10,
        lineHeight: 13,
      },

      unreadDot: {
        width: 7,
        height: 7,

        marginTop: 4,

        borderRadius: 4,

        backgroundColor:
          colors.plum,

        flexShrink: 0,
      },

      bottomSpace: {
        height: 72,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );