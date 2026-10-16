import React, {
  useMemo,
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
  useFocusEffect,
  useRouter,
} from "expo-router";

import {
  cancelBooking,
  getBookings,
  getBookingActions,
  requestBookingReschedule,
  withdrawBookingReschedule,
  withdrawBookingCancellation,
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

type BookingTab =
  | "upcoming"
  | "requests"
  | "history";

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

  const [workingId, setWorkingId] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);

  const [tab, setTab] =
    useState<BookingTab>(
      "upcoming",
    );

  useFocusEffect(
    React.useCallback(() => {
      let active = true;

      const load =
        async () => {
          setLoading(true);

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
            setNextOffset(response.pagination.nextOffset);
            setLoadMoreError(null);
            setErrorMessage(
              null,
            );
            setSessionExpired(false);
          } catch (error) {
            if (!active) {
              return;
            }

            if (
              error instanceof ApiError &&
              error.status === 401
            ) {
              setSessionExpired(true);
              setErrorMessage(
                "Entre na sua conta para acompanhar seus agendamentos.",
              );
            } else {
              setSessionExpired(false);
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
    }, []),
  );

  const visibleItems = useMemo(() => items.filter((booking) => {
    if (tab === "requests") {
      return booking.cancellationRequestStatus === "pending"
        || booking.rescheduleRequestStatus === "pending";
    }
    if (tab === "history") {
      return booking.status === "completed" || booking.status === "cancelled"
        || booking.status === "no_show"
        || (booking.status === "confirmed" && new Date(booking.slot.startsAt).getTime() <= Date.now());
    }
    return (booking.status === "pending" || booking.status === "confirmed")
      && new Date(booking.slot.startsAt).getTime() > Date.now();
  }), [items, tab]);

  const refresh =
    async () => {
      const response =
        await getBookings({
          limit: 50,
        });

      setItems(
        response.items,
      );
      setNextOffset(response.pagination.nextOffset);
      setLoadMoreError(null);
    };

  const loadMore = async () => {
    if (nextOffset === null || loadingMore) {
      return;
    }

    setLoadingMore(true);
    setLoadMoreError(null);
    try {
      const response = await getBookings({ limit: 50, offset: nextOffset });
      setItems((current) => {
        const known = new Set(current.map((item) => item.id));
        return [...current, ...response.items.filter((item) => !known.has(item.id))];
      });
      setNextOffset(response.pagination.nextOffset);
    } catch (error) {
      setLoadMoreError(
        error instanceof Error
          ? error.message
          : "Não foi possível carregar mais agendamentos.",
      );
    } finally {
      setLoadingMore(false);
    }
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
          "Não foi possível processar a solicitação",
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
      booking.status === "pending" ? "Liberar horário?" : "Solicitar cancelamento?",
      booking.status === "pending"
        ? "Esta retenção temporária será liberada."
        : "A reserva permanecerá confirmada até a análise do profissional executor.",
      [
        {
          text: "Manter reserva",
          style: "cancel",
        },
        {
          text: booking.status === "pending" ? "Liberar horário" : "Enviar solicitação",
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

  const runAction = async (bookingId: string, action: () => Promise<unknown>) => {
    if (workingId) return;
    setWorkingId(bookingId);
    try {
      await action();
      await refresh();
    } catch (error) {
      Alert.alert("Não foi possível concluir", error instanceof Error ? error.message : "Tente novamente.");
    } finally {
      setWorkingId(null);
    }
  };

  const chooseReschedule = async (booking: Booking) => {
    try {
      const actions = await getBookingActions(booking.id);
      if (actions.rescheduleRequestStatus === "pending") {
        Alert.alert("Solicitação pendente", "O horário original permanece reservado até a análise.");
        return;
      }
      if (!actions.rescheduleSlots.length) {
        Alert.alert("Sem novos horários", "Não há alternativas válidas para esta oferta agora.");
        return;
      }
      Alert.alert(
        "Solicitar outro horário",
        "Escolha entre as duas primeiras opções disponíveis. O executor deverá aprovar; sua reserva original permanece confirmada.",
        [
          ...actions.rescheduleSlots.slice(0, 2).map((slot) => ({
            text: `${slot.localDate} às ${slot.localTime}`,
            onPress: () => void runAction(booking.id,
              () => requestBookingReschedule(booking.id, slot.id)),
          })),
          { text: "Voltar", style: "cancel" as const },
        ],
      );
    } catch (error) {
      Alert.alert("Horários indisponíveis", error instanceof Error ? error.message : "Tente novamente.");
    }
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

        {!errorMessage &&
        items.length > 0 ? (
          <View
            style={
              styles.tabs
            }
          >
            {(
              [
                {
                  id:
                    "upcoming",
                  label:
                    "Próximos",
                },
                {
                  id: "requests",
                  label: "Solicitações",
                },
                {
                  id:
                    "history",
                  label:
                    "Histórico",
                },
              ] as const
            ).map(
              (item) => {
                const selected =
                  tab ===
                  item.id;

                return (
                  <Pressable
                    key={
                      item.id
                    }
                    accessibilityRole="button"
                    accessibilityState={{
                      selected,
                    }}
                    onPress={() =>
                      setTab(
                        item.id,
                      )
                    }
                    style={[
                      styles.tab,
                      selected &&
                        styles.tabActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.tabText,
                        selected &&
                          styles.tabTextActive,
                      ]}
                    >
                      {
                        item.label
                      }
                    </Text>
                  </Pressable>
                );
              },
            )}
          </View>
        ) : null}

        {errorMessage ? (
          <EmptyState
            title="Não foi possível abrir seus agendamentos"
            description={
              errorMessage
            }
            actionLabel={sessionExpired ? "Entrar" : "Tentar novamente"}
            onActionPress={() => {
              if (sessionExpired) {
                router.push({
                  pathname: "/login",
                  params: { returnTo: "bookings" },
                });
                return;
              }

              setLoading(true);
              void getBookings({ limit: 50 })
                .then((response) => {
                  setItems(response.items);
                  setNextOffset(response.pagination.nextOffset);
                  setLoadMoreError(null);
                  setErrorMessage(null);
                  setSessionExpired(false);
                })
                .catch((error: unknown) => {
                  const needsLogin = error instanceof ApiError && error.status === 401;
                  setSessionExpired(needsLogin);
                  setErrorMessage(
                    needsLogin
                      ? "Entre na sua conta para acompanhar seus agendamentos."
                      : error instanceof Error
                        ? error.message
                        : "Não foi possível carregar seus agendamentos.",
                  );
                })
                .finally(() => setLoading(false));
            }}
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
        ) : visibleItems.length ===
          0 ? (
          <EmptyState
            title={
              tab ===
                "upcoming"
                ? "Nenhum agendamento futuro"
                : tab === "requests" ? "Nenhuma solicitação pendente" : "Seu histórico está vazio"
            }
            description={
              tab ===
                "upcoming"
                ? "Quando você reservar uma experiência, ela aparece aqui."
                : tab === "requests" ? "Pedidos de cancelamento e reagendamento em análise aparecem aqui." : "Atendimentos concluídos ou cancelados aparecem aqui."
            }
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
            {visibleItems.map(
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

                  {booking.cancellationRequestStatus === "pending" ? (
                    <Text style={styles.metaText}>Cancelamento solicitado — aguardando executor.</Text>
                  ) : null}
                  {booking.rescheduleRequestStatus === "pending" ? (
                    <Text style={styles.metaText}>Reagendamento solicitado — horário original mantido.</Text>
                  ) : null}

                  <View
                    style={
                      styles.actions
                    }
                  >
                    <Button
                      title={booking.status === "pending" ? "Continuar confirmação" : "Ver experiência"}
                      variant="secondary"
                      compact
                      onPress={() => {
                        if (booking.status === "pending") {
                          router.push({
                            pathname: "/booking/[serviceId]",
                            params: {
                              serviceId: booking.experience.slug,
                              bookingId: booking.id,
                            },
                          });
                        } else {
                          router.push(`/booking/${booking.experience.slug}`);
                        }
                      }}
                    />

                    {booking.status === "confirmed" && !booking.rescheduleRequestStatus ? (
                      <Button title="Solicitar reagendamento" variant="secondary" compact
                        loading={workingId === booking.id}
                        onPress={() => void chooseReschedule(booking)} />
                    ) : null}
                    {booking.rescheduleRequestStatus === "pending" ? (
                      <Button title="Retirar reagendamento" variant="ghost" compact
                        loading={workingId === booking.id}
                        onPress={() => void runAction(booking.id,
                          () => withdrawBookingReschedule(booking.id))} />
                    ) : null}
                    {booking.cancellationRequestStatus === "pending" ? (
                      <Button title="Retirar cancelamento" variant="ghost" compact
                        loading={workingId === booking.id}
                        onPress={() => void runAction(booking.id,
                          () => withdrawBookingCancellation(booking.id))} />
                    ) : null}
                    {(booking.canCancel || (booking.canRequestCancellation && !booking.cancellationRequestStatus)) ? (
                      <Button
                        title={booking.status === "pending" ? "Liberar horário" : "Solicitar cancelamento"}
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
                    ) : booking.cancellationRequestStatus === "pending" ? (
                      <Text>Solicitação de cancelamento pendente de análise pelo executor.</Text>
                    ) : null}
                  </View>
                </View>
              ),
            )}
          </View>
        )}

        {!errorMessage && nextOffset !== null ? (
          <View style={styles.actions}>
            <Button
              title={loadingMore ? "Carregando..." : "Carregar mais agendamentos"}
              variant="secondary"
              loading={loadingMore}
              onPress={() => void loadMore()}
            />
          </View>
        ) : null}

        {loadMoreError ? (
          <Text accessibilityRole="alert" style={styles.metaTextMuted}>
            {loadMoreError}
          </Text>
        ) : null}

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

      tabs: {
        marginTop:
          spacing.xl,
        flexDirection:
          "row",
        gap: spacing.sm,
      },

      tab: {
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.lg,
        alignItems:
          "center",
        justifyContent:
          "center",
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.glassSoft,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      tabActive: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },

      tabText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },

      tabTextActive: {
        color:
          colors.onBrandPrimary,
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
