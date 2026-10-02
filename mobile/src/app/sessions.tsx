import React, {
  useEffect,
  useState,
} from "react";
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

import {
  getDeviceSessions,
  revokeDeviceSession,
  revokeOtherDeviceSessions,
  type DeviceSession,
} from "@/api/auth";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

function platformLabel(
  platform: string,
) {
  if (platform === "ios") {
    return "iOS";
  }

  if (
    platform === "android"
  ) {
    return "Android";
  }

  if (platform === "web") {
    return "Web";
  }

  return "Dispositivo";
}

function formatLastSeen(
  value: string,
) {
  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(
    new Date(value),
  );
}

export default function SessionsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [
    sessions,
    setSessions,
  ] =
    useState<DeviceSession[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    actionId,
    setActionId,
  ] =
    useState<string | null>(
      null,
    );

  const [
    revokingOthers,
    setRevokingOthers,
  ] = useState(false);

  const [
    errorMessage,
    setErrorMessage,
  ] =
    useState<string | null>(
      null,
    );

  const load =
    async () => {
      const response =
        await getDeviceSessions();

      setSessions(
        response.items,
      );
    };

  useEffect(() => {
    let active = true;

    const run =
      async () => {
        try {
          const response =
            await getDeviceSessions();

          if (active) {
            setSessions(
              response.items,
            );
          }
        } catch (error) {
          if (active) {
            setErrorMessage(
              error instanceof Error
                ? error.message
                : "Não foi possível carregar suas sessões.",
            );
          }
        } finally {
          if (active) {
            setLoading(false);
          }
        }
      };

    void run();

    return () => {
      active = false;
    };
  }, []);

  const handleRevoke =
    async (
      session: DeviceSession,
    ) => {
      setActionId(
        session.id,
      );

      try {
        await revokeDeviceSession(
          session.id,
        );
        await load();
      } catch (error) {
        Alert.alert(
          "Não foi possível encerrar",
          error instanceof Error
            ? error.message
            : "Tente novamente em instantes.",
        );
      } finally {
        setActionId(
          null,
        );
      }
    };

  const confirmRevoke = (
    session: DeviceSession,
  ) => {
    Alert.alert(
      "Encerrar esta sessão?",
      "Esse dispositivo precisará entrar novamente no IDDUN.",
      [
        {
          text: "Cancelar",
          style: "cancel",
        },
        {
          text: "Encerrar",
          style: "destructive",
          onPress: () => {
            void handleRevoke(
              session,
            );
          },
        },
      ],
    );
  };

  const handleRevokeOthers =
    async () => {
      setRevokingOthers(
        true,
      );

      try {
        await revokeOtherDeviceSessions();
        await load();
      } catch (error) {
        Alert.alert(
          "Não foi possível encerrar as outras sessões",
          error instanceof Error
            ? error.message
            : "Tente novamente em instantes.",
        );
      } finally {
        setRevokingOthers(
          false,
        );
      }
    };

  const otherSessions =
    sessions.filter(
      (item) =>
        !item.current,
    );

  if (loading) {
    return (
      <View
        style={
          styles.loading
        }
      >
        <ActivityIndicator
          color={
            colors.plum
          }
        />
        <Text
          style={
            styles.loadingText
          }
        >
          Carregando sessões…
        </Text>
      </View>
    );
  }

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
                  "/(tabs)/profile",
                );
              }
            }}
            style={
              styles.backButton
            }
          >
            <Icon
              name="arrow-left"
              size={20}
              color={
                colors.onSurface
              }
            />
          </Pressable>

          <Text
            style={
              styles.headerTitle
            }
          >
            Dispositivos
          </Text>

          <View
            style={
              styles.headerSpacer
            }
          />
        </View>

        <View
          style={
            styles.intro
          }
        >
          <Text
            style={
              styles.eyebrow
            }
          >
            SEGURANÇA DA CONTA
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Onde sua conta está conectada.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            O IDDUN mostra apenas a plataforma e o último uso da sessão. Não armazenamos localização ou IP nesta tela.
          </Text>
        </View>

        {errorMessage ? (
          <EmptyState
            title="Não foi possível carregar as sessões"
            description={
              errorMessage
            }
            actionLabel="Voltar ao perfil"
            onActionPress={() =>
              router.replace(
                "/(tabs)/profile",
              )
            }
          />
        ) : (
          <View
            style={
              styles.list
            }
          >
            {sessions.map(
              (session) => (
                <View
                  key={
                    session.id
                  }
                  style={
                    styles.card
                  }
                >
                  <View
                    style={
                      styles.cardIcon
                    }
                  >
                    <Icon
                      name={
                        session.platform ===
                        "web"
                          ? "monitor"
                          : "smartphone"
                      }
                      size={20}
                      color={
                        colors.plum
                      }
                    />
                  </View>

                  <View
                    style={
                      styles.cardBody
                    }
                  >
                    <View
                      style={
                        styles.cardTitleRow
                      }
                    >
                      <Text
                        style={
                          styles.cardTitle
                        }
                      >
                        {
                          session.deviceName
                        }
                      </Text>

                      {session.current ? (
                        <View
                          style={
                            styles.currentBadge
                          }
                        >
                          <Text
                            style={
                              styles.currentBadgeText
                            }
                          >
                            ESTE DISPOSITIVO
                          </Text>
                        </View>
                      ) : null}
                    </View>

                    <Text
                      style={
                        styles.cardMeta
                      }
                    >
                      {
                        platformLabel(
                          session.platform,
                        )
                      }
                      {" · "}
                      Último uso{" "}
                      {
                        formatLastSeen(
                          session.lastSeenAt,
                        )
                      }
                    </Text>

                    {!session.current ? (
                      <Pressable
                        accessibilityRole="button"
                        onPress={() =>
                          confirmRevoke(
                            session,
                          )
                        }
                        disabled={
                          actionId ===
                          session.id
                        }
                        style={
                          styles.revokeButton
                        }
                      >
                        <Text
                          style={
                            styles.revokeText
                          }
                        >
                          {actionId ===
                          session.id
                            ? "Encerrando…"
                            : "Encerrar sessão"}
                        </Text>
                      </Pressable>
                    ) : null}
                  </View>
                </View>
              ),
            )}

            {otherSessions.length >
            0 ? (
              <View
                style={
                  styles.bulkAction
                }
              >
                <Button
                  title="Encerrar todas as outras sessões"
                  variant="secondary"
                  loading={
                    revokingOthers
                  }
                  onPress={() =>
                    void handleRevokeOthers()
                  }
                  fullWidth
                />
              </View>
            ) : null}
          </View>
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

      loading: {
        flex: 1,
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.md,
        backgroundColor:
          colors.surface,
      },

      loadingText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
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

      backButton: {
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

      headerTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 14,
      },

      headerSpacer: {
        width:
          touch.minimum,
      },

      intro: {
        marginTop:
          spacing.xxl,
      },

      eyebrow: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        letterSpacing: 1.4,
      },

      title: {
        maxWidth: 350,
        marginTop:
          spacing.sm,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 30,
        lineHeight: 36,
      },

      description: {
        maxWidth: 360,
        marginTop:
          spacing.md,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 19,
      },

      list: {
        marginTop:
          spacing.xxl,
        gap: spacing.md,
      },

      card: {
        padding:
          spacing.lg,
        flexDirection:
          "row",
        gap: spacing.md,
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      cardIcon: {
        width: 42,
        height: 42,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plumSoft,
      },

      cardBody: {
        flex: 1,
      },

      cardTitleRow: {
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        alignItems:
          "center",
        gap: spacing.sm,
      },

      cardTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 13,
      },

      currentBadge: {
        paddingHorizontal: 7,
        paddingVertical: 4,
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.plumSoft,
      },

      currentBadgeText: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 8,
        letterSpacing: 0.7,
      },

      cardMeta: {
        marginTop:
          spacing.xs,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 16,
      },

      revokeButton: {
        minHeight:
          touch.minimum,
        alignSelf:
          "flex-start",
        justifyContent:
          "center",
        marginTop:
          spacing.sm,
      },

      revokeText: {
        color:
          colors.error,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },

      bulkAction: {
        marginTop:
          spacing.sm,
      },

      bottomSpace: {
        height: 110,
      },
    }),
  );
