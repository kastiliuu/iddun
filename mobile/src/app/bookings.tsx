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
  cancelBooking,
  getBookings,
  type Booking,
} from "@/api/bookings";
import { ApiError } from "@/api/client";
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

const STATUS_LABELS: Record<
  Booking["status"],
  string
> = {
  pending:
    "Aguardando confirmação",
  confirmed: "Confirmada",
  completed: "Concluída",
  cancelled: "Cancelada",
  no_show: "Não compareceu",
};

function formatCurrency(
  value: number,
) {
  return new Intl.NumberFormat(
    "pt-BR",
    {
      style: "currency",
      currency: "BRL",
    },
  ).format(value);
}

function formatDate(
  value: string,
) {
  const date = new Date(
    `${value}T12:00:00`,
  );

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      weekday: "short",
      day: "2-digit",
      month: "short",
      year: "numeric",
    },
  ).format(date);
}

export default function BookingsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [
    items,
    setItems,
  ] = useState<Booking[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    errorMessage,
    setErrorMessage,
  ] =
    useState<string | null>(
      null,
    );

  const [
    cancellingId,
    setCancellingId,
  ] =
    useState<string | null>(
      null,
    );

  useEffect(() => {
    let active = true;

    const load =
      async () => {
        try {
          const response =
            await getBookings({
              limit: 50,
            });

          if (!active) {
            return;
          }

          setItems(
            response.items,
          );
        } catch (error) {
          if (!active) {
            return;
          }

          if (
            error instanceof ApiError &&
            error.status === 401
          ) {
            setErrorMessage(
              "Entre na sua conta para acompanhar seus agendamentos.",
            );
          } else {
            setErrorMessage(
              error instanceof Error
                ? error.message
                : "Não foi possível carregar seus agendamentos.",
            );
          }
        } finally {
          if (active) {
            setLoading(false);
          }
        }
      };

    void load();

    return () => {
      active = false;
    };
  }, []);

  const refresh =
    async () => {
      const response =
        await getBookings({
          limit: 50,
        });

      setItems(
        response.items,
      );
    };

  const handleCancel =
    async (
      booking: Booking,
    ) => {
      setCancellingId(
        booking.id,
      );

      try {
        await cancelBooking(
          booking.id,
        );

        await refresh();
      } catch (error) {
        Alert.alert(
          "Não foi possível cancelar",
          error instanceof Error
            ? error.message
            : "Tente novamente em instantes.",
        );
      } finally {
        setCancellingId(
          null,
        );
      }
    };

  const requestCancel = (
    booking: Booking,
  ) => {
    Alert.alert(
      "Cancelar reserva?",
      "O horário será liberado novamente se ainda estiver dentro das regras de agendamento.",
      [
        {
          text: "Manter reserva",
          style: "cancel",
        },
        {
          text: "Cancelar reserva",
          style: "destructive",
          onPress: () => {
            void handleCancel(
              booking,
            );
          },
        },
      ],
    );
  };

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
          Carregando seus agendamentos…
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

          <Text
            style={
              styles.headerTitle
            }
          >
            Meus agendamentos
          </Text>

          <View
            style={
              styles.headerPlaceholder
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
            SUA JORNADA
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Experiências marcadas com você.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Acompanhe reservas confirmadas, histórico e próximos horários em um só lugar.
          </Text>
        </View>

        {errorMessage ? (
          <EmptyState
            title="Não foi possível abrir seus agendamentos"
            description={
              errorMessage
            }
            actionLabel="Entrar"
            onActionPress={() =>
              router.push({
                pathname: "/login",
                params: {
                  returnTo: "bookings",
                },
              })
            }
          />
        ) : items.length ===
          0 ? (
          <EmptyState
            title="Sua primeira experiência começa aqui."
            description="Descubra profissionais e horários publicados no IDDUN."
            actionLabel="Explorar experiências"
            onActionPress={() =>
              router.replace(
                "/(tabs)/discover",
              )
            }
          />
        ) : (
          <View
            style={
              styles.list
            }
          >
            {items.map(
              (booking) => (
                <View
                  key={
                    booking.id
                  }
                  style={
                    styles.card
                  }
                >
                  <View
                    style={
                      styles.cardTop
                    }
                  >
                    <View
                      style={
                        styles.statusBadge
                      }
                    >
                      <Text
                        style={
                          styles.statusText
                        }
                      >
                        {
                          STATUS_LABELS[
                            booking.status
                          ]
                        }
                      </Text>
                    </View>

                    <Text
                      style={
                        styles.price
                      }
                    >
                      {
                        formatCurrency(
                          booking.price,
                        )
                      }
                    </Text>
                  </View>

                  <Text
                    style={
                      styles.cardTitle
                    }
                  >
                    {
                      booking
                        .experience
                        .title
                    }
                  </Text>

                  <Text
                    style={
                      styles.cardProfessional
                    }
                  >
                    {
                      booking
                        .professional
                        .name
                    }
                  </Text>

                  <View
                    style={
                      styles.meta
                    }
                  >
                    <View
                      style={
                        styles.metaItem
                      }
                    >
                      <Icon
                        name="calendar"
                        size={15}
                        color={
                          colors.plum
                        }
                      />
                      <Text
                        style={
                          styles.metaText
                        }
                      >
                        {
                          formatDate(
                            booking
                              .slot
                              .localDate,
                          )
                        }
                      </Text>
                    </View>

                    <View
                      style={
                        styles.metaItem
                      }
                    >
                      <Icon
                        name="clock"
                        size={15}
                        color={
                          colors.plum
                        }
                      />
                      <Text
                        style={
                          styles.metaText
                        }
                      >
                        {
                          booking
                            .slot
                            .localTime
                        }
                      </Text>
                    </View>
                  </View>

                  {booking
                    .establishment ? (
                    <View
                      style={
                        styles.metaItem
                      }
                    >
                      <Icon
                        name="map-pin"
                        size={15}
                        color={
                          colors.muted
                        }
                      />
                      <Text
                        style={
                          styles.metaTextMuted
                        }
                      >
                        {
                          booking
                            .establishment
                            .name
                        }
                      </Text>
                    </View>
                  ) : null}

                  <View
                    style={
                      styles.actions
                    }
                  >
                    <Button
                      title="Reservar novamente"
                      variant="secondary"
                      compact
                      onPress={() =>
                        router.push(
                          `/booking/${booking.experience.slug}`,
                        )
                      }
                    />

                    {booking.canCancel ? (
                      <Button
                        title="Cancelar"
                        variant="ghost"
                        compact
                        loading={
                          cancellingId ===
                          booking.id
                        }
                        onPress={() =>
                          requestCancel(
                            booking,
                          )
                        }
                      />
                    ) : null}
                  </View>
                </View>
              ),
            )}
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

      headerTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 14,
      },

      headerPlaceholder: {
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
        maxWidth: 340,
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
        maxWidth: 350,
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
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      cardTop: {
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "space-between",
        gap: spacing.md,
      },

      statusBadge: {
        paddingHorizontal:
          spacing.sm,
        paddingVertical: 6,
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.plumSoft,
      },

      statusText: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
      },

      price: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 13,
      },

      cardTitle: {
        marginTop:
          spacing.lg,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 22,
        lineHeight: 27,
      },

      cardProfessional: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 12,
      },

      meta: {
        marginTop:
          spacing.lg,
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap: spacing.md,
      },

      metaItem: {
        marginTop:
          spacing.sm,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.xs,
      },

      metaText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 11,
      },

      metaTextMuted: {
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 11,
      },

      actions: {
        marginTop:
          spacing.lg,
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap: spacing.sm,
      },

      bottomSpace: {
        height: 110,
      },

      pressed: {
        opacity: 0.72,
      },
    }),
  );
