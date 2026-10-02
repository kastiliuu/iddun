import React, {
  useEffect,
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
import { Image } from "expo-image";
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import * as Haptics from "expo-haptics";

import {
  cancelBooking,
  confirmBooking,
  holdExperienceSlot,
  type Booking,
} from "@/api/bookings";
import {
  getExperienceAvailability,
  getRealExperience,
  type CatalogExperience,
  type ExperienceAvailabilityDay,
  type ExperienceAvailabilityResponse,
  type ExperienceAvailabilitySlot,
} from "@/api/experiences";
import { ApiError } from "@/api/client";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  touch,
  useTheme,
} from "@/theme";

type BookingStep =
  | "date"
  | "time"
  | "confirm"
  | "success";

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

function formatDuration(
  minutes: number,
) {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours =
    Math.floor(
      minutes / 60,
    );

  const remaining =
    minutes % 60;

  return remaining
    ? `${hours}h ${remaining}min`
    : `${hours}h`;
}

function dateAtNoon(
  value: string,
) {
  return new Date(
    `${value}T12:00:00`,
  );
}

function formatDayCard(
  value: string,
) {
  const date =
    dateAtNoon(value);

  return {
    weekday:
      new Intl.DateTimeFormat(
        "pt-BR",
        {
          weekday: "short",
        },
      )
        .format(date)
        .replace(".", ""),
    day:
      new Intl.DateTimeFormat(
        "pt-BR",
        {
          day: "2-digit",
        },
      ).format(date),
    month:
      new Intl.DateTimeFormat(
        "pt-BR",
        {
          month: "short",
        },
      )
        .format(date)
        .replace(".", ""),
    label:
      new Intl.DateTimeFormat(
        "pt-BR",
        {
          weekday: "long",
          day: "2-digit",
          month: "long",
        },
      ).format(date),
  };
}

function formatSlotTime(
  startsAt: string,
  timezone: string,
) {
  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: timezone,
    },
  ).format(
    new Date(startsAt),
  );
}

function formatHoldExpiration(
  value: string | null,
  timezone: string,
) {
  if (!value) {
    return null;
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: timezone,
    },
  ).format(
    new Date(value),
  );
}

export default function BookingScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const params =
    useLocalSearchParams<{
      serviceId: string;
    }>();

  const experienceSlug =
    Array.isArray(
      params.serviceId,
    )
      ? params.serviceId[0]
      : params.serviceId;

  const [
    experience,
    setExperience,
  ] =
    useState<CatalogExperience | null>(
      null,
    );

  const [
    availability,
    setAvailability,
  ] =
    useState<ExperienceAvailabilityResponse | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    loadError,
    setLoadError,
  ] =
    useState<string | null>(
      null,
    );

  const [step, setStep] =
    useState<BookingStep>(
      "date",
    );

  const [
    selectedDate,
    setSelectedDate,
  ] =
    useState<string | null>(
      null,
    );

  const [
    selectedSlotId,
    setSelectedSlotId,
  ] =
    useState<number | null>(
      null,
    );

  const [
    booking,
    setBooking,
  ] =
    useState<Booking | null>(
      null,
    );

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  useEffect(() => {
    const controller =
      new AbortController();

    const load =
      async () => {
        if (!experienceSlug) {
          setLoadError(
            "Experiência não encontrada.",
          );
          setLoading(false);
          return;
        }

        try {
          const [
            experienceResponse,
            availabilityResponse,
          ] =
            await Promise.all([
              getRealExperience(
                experienceSlug,
                controller.signal,
              ),
              getExperienceAvailability(
                experienceSlug,
                controller.signal,
              ),
            ]);

          if (
            controller.signal.aborted
          ) {
            return;
          }

          setExperience(
            experienceResponse,
          );
          setAvailability(
            availabilityResponse,
          );

          setSelectedDate(
            (
              current,
            ) => {
              if (
                current &&
                availabilityResponse.days.some(
                  (day) =>
                    day.date ===
                    current,
                )
              ) {
                return current;
              }

              return (
                availabilityResponse
                  .days[0]?.date ??
                null
              );
            },
          );
        } catch (
          error: unknown
        ) {
          if (
            error instanceof Error &&
            error.name ===
              "AbortError"
          ) {
            return;
          }

          if (
            error instanceof ApiError &&
            error.status === 404
          ) {
            setLoadError(
              "Essa experiência não está publicada no momento.",
            );
          } else {
            setLoadError(
              "Não foi possível carregar a disponibilidade agora.",
            );
          }
        } finally {
          if (
            !controller.signal.aborted
          ) {
            setLoading(false);
          }
        }
      };

    void load();

    return () => {
      controller.abort();
    };
  }, [experienceSlug]);

  const selectedDay =
    useMemo<
      ExperienceAvailabilityDay | undefined
    >(
      () =>
        availability?.days.find(
          (item) =>
            item.date ===
            selectedDate,
        ),
      [
        availability,
        selectedDate,
      ],
    );

  const selectedSlot =
    useMemo<
      ExperienceAvailabilitySlot | undefined
    >(
      () =>
        selectedDay?.slots.find(
          (slot) =>
            slot.id ===
            selectedSlotId,
        ),
      [
        selectedDay,
        selectedSlotId,
      ],
    );

  const timezone =
    availability?.timezone ??
    "America/Sao_Paulo";

  const selectedDateLabel =
    selectedDate
      ? formatDayCard(
          selectedDate,
        ).label
      : null;

  const holdExpiration =
    formatHoldExpiration(
      booking?.holdExpiresAt ??
        null,
      timezone,
    );

  const refreshAvailability =
    async () => {
      if (!experienceSlug) {
        return;
      }

      const response =
        await getExperienceAvailability(
          experienceSlug,
        );

      setAvailability(
        response,
      );
      setSelectedDate(
        (current) => {
          if (
            current &&
            response.days.some(
              (day) =>
                day.date ===
                current,
            )
          ) {
            return current;
          }

          return (
            response.days[0]
              ?.date ??
            null
          );
        },
      );
    };

  const leavePendingHold =
    async () => {
      if (
        booking?.status !==
        "pending"
      ) {
        return;
      }

      try {
        await cancelBooking(
          booking.id,
        );
      } catch {
        // O hold expira no backend mesmo
        // se o aparelho ficar offline.
      }

      setBooking(null);
    };

  const handleBack =
    async () => {
      if (submitting) {
        return;
      }

      if (
        step === "success"
      ) {
        router.replace(
          "/(tabs)",
        );
        return;
      }

      if (
        step === "confirm"
      ) {
        setSubmitting(true);

        await leavePendingHold();

        try {
          await refreshAvailability();
        } catch {
          // A tela continua utilizável com
          // a última disponibilidade conhecida.
        }

        setSelectedSlotId(
          null,
        );
        setStep("time");
        setSubmitting(false);
        return;
      }

      if (
        step === "time"
      ) {
        setSelectedSlotId(
          null,
        );
        setStep("date");
        return;
      }

      if (
        router.canGoBack()
      ) {
        router.back();
      } else {
        router.replace(
          "/(tabs)/discover",
        );
      }
    };

  const handleContinue =
    async () => {
      Haptics
        .impactAsync(
          Haptics
            .ImpactFeedbackStyle
            .Light,
        )
        .catch(() => {});

      if (
        step === "date"
      ) {
        if (!selectedDay) {
          return;
        }

        setStep("time");
        return;
      }

      if (
        step !== "time" ||
        !selectedSlot ||
        !experienceSlug
      ) {
        return;
      }

      setSubmitting(true);

      try {
        const response =
          await holdExperienceSlot(
            experienceSlug,
            selectedSlot.id,
          );

        setBooking(
          response.booking,
        );
        setStep(
          "confirm",
        );
      } catch (error) {
        if (
          error instanceof ApiError &&
          error.status === 401
        ) {
          Alert.alert(
            "Entre para reservar",
            "Faça login na sua conta IDDUN e tente novamente.",
            [
              {
                text: "Agora não",
                style: "cancel",
              },
              {
                text: "Entrar",
                onPress: () =>
                  router.push({
                    pathname: "/login",
                    params: {
                      returnToBooking:
                        experienceSlug,
                    },
                  }),
              },
            ],
          );
        } else if (
          error instanceof ApiError &&
          error.status === 409
        ) {
          setSelectedSlotId(
            null,
          );

          try {
            await refreshAvailability();
          } catch {
            // O alerta principal continua sendo
            // o conflito do horário.
          }

          Alert.alert(
            "Horário indisponível",
            error.message,
          );
        } else {
          Alert.alert(
            "Não foi possível reservar",
            error instanceof Error
              ? error.message
              : "Tente novamente em instantes.",
          );
        }
      } finally {
        setSubmitting(false);
      }
    };

  const handleConfirm =
    async () => {
      if (
        !booking ||
        booking.status !==
          "pending"
      ) {
        return;
      }

      setSubmitting(true);

      try {
        const response =
          await confirmBooking(
            booking.id,
          );

        setBooking(
          response.booking,
        );
        setStep(
          "success",
        );

        Haptics
          .notificationAsync(
            Haptics
              .NotificationFeedbackType
              .Success,
          )
          .catch(() => {});
      } catch (error) {
        if (
          error instanceof ApiError &&
          error.status === 409
        ) {
          setBooking(null);
          setSelectedSlotId(
            null,
          );
          setStep("time");

          try {
            await refreshAvailability();
          } catch {
            // A mensagem de conflito já orienta
            // a pessoa a escolher outro horário.
          }

          Alert.alert(
            "Reserva não confirmada",
            error.message,
          );
        } else {
          Alert.alert(
            "Não foi possível confirmar",
            error instanceof Error
              ? error.message
              : "Tente novamente em instantes.",
          );
        }
      } finally {
        setSubmitting(false);
      }
    };

  if (loading) {
    return (
      <View
        style={
          styles.loadingState
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
          Consultando disponibilidade real…
        </Text>
      </View>
    );
  }

  if (
    loadError ||
    !experience ||
    !availability
  ) {
    return (
      <View
        style={
          styles.container
        }
      >
        <View
          style={
            styles.headerOnly
          }
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => {
              void handleBack();
            }}
            style={
              styles.headerButton
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
        </View>

        <EmptyState
          title="Agendamento indisponível"
          description={
            loadError ??
            "Essa experiência não pode ser reservada agora."
          }
          actionLabel="Descobrir experiências"
          onActionPress={() =>
            router.replace(
              "/(tabs)/discover",
            )
          }
        />
      </View>
    );
  }

  const stepNumber =
    step === "date"
      ? 1
      : step === "time"
        ? 2
        : step ===
            "confirm"
          ? 3
          : 4;

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
            disabled={
              submitting
            }
            onPress={() => {
              void handleBack();
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

          <View
            style={
              styles.headerCenter
            }
          >
            <Text
              style={
                styles.headerTitle
              }
            >
              Agendamento
            </Text>

            {step !==
            "success" ? (
              <Text
                style={
                  styles.headerStep
                }
              >
                Etapa{" "}
                {stepNumber} de 3
              </Text>
            ) : null}
          </View>

          <View
            style={
              styles.headerPlaceholder
            }
          />
        </View>

        {step !==
        "success" ? (
          <View
            style={
              styles.progress
            }
          >
            {[1, 2, 3].map(
              (item) => (
                <View
                  key={item}
                  style={[
                    styles.progressBar,
                    stepNumber >=
                      item &&
                      styles.progressBarActive,
                  ]}
                />
              ),
            )}
          </View>
        ) : null}

        {step !==
        "success" ? (
          <View
            style={
              styles.experienceCard
            }
          >
            <Image
              source={{
                uri:
                  experience.imageUrl,
              }}
              style={
                styles.experienceImage
              }
              contentFit="cover"
              accessibilityLabel={
                experience.title
              }
            />

            <View
              style={
                styles.experienceBody
              }
            >
              <Text
                style={
                  styles.experienceEyebrow
                }
              >
                {
                  experience.categoryLabel
                }
              </Text>

              <Text
                style={
                  styles.experienceTitle
                }
                numberOfLines={2}
              >
                {
                  experience.title
                }
              </Text>

              <Text
                style={
                  styles.experienceMeta
                }
                numberOfLines={2}
              >
                {
                  experience.professional
                }
                {" · "}
                {
                  experience.location
                }
              </Text>
            </View>
          </View>
        ) : null}

        {step ===
        "date" ? (
          <>
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
                QUANDO
              </Text>

              <Text
                style={
                  styles.title
                }
              >
                Escolha o melhor dia.
              </Text>

              <Text
                style={
                  styles.description
                }
              >
                A disponibilidade abaixo vem da agenda real desta experiência.
              </Text>
            </View>

            {availability
              .days
              .length >
            0 ? (
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={
                  false
                }
                contentContainerStyle={
                  styles.dateList
                }
              >
                {availability.days.map(
                  (day) => {
                    const card =
                      formatDayCard(
                        day.date,
                      );
                    const selected =
                      day.date ===
                      selectedDate;

                    return (
                      <Pressable
                        key={
                          day.date
                        }
                        accessibilityRole="button"
                        accessibilityLabel={
                          card.label
                        }
                        accessibilityState={{
                          selected,
                        }}
                        onPress={() => {
                          setSelectedDate(
                            day.date,
                          );
                          setSelectedSlotId(
                            null,
                          );

                          Haptics
                            .selectionAsync()
                            .catch(
                              () => {},
                            );
                        }}
                        style={({
                          pressed,
                        }) => [
                          styles.dateCard,
                          selected &&
                            styles.dateCardSelected,
                          pressed &&
                            styles.pressed,
                        ]}
                      >
                        <Text
                          style={[
                            styles.dateWeekday,
                            selected &&
                              styles.dateTextSelected,
                          ]}
                        >
                          {
                            card.weekday
                          }
                        </Text>

                        <Text
                          style={[
                            styles.dateDay,
                            selected &&
                              styles.dateTextSelected,
                          ]}
                        >
                          {card.day}
                        </Text>

                        <Text
                          style={[
                            styles.dateMonth,
                            selected &&
                              styles.dateTextSelected,
                          ]}
                        >
                          {card.month}
                        </Text>
                      </Pressable>
                    );
                  },
                )}
              </ScrollView>
            ) : (
              <EmptyState
                title="Sem horários disponíveis"
                description="Esse profissional ainda não publicou novos horários para esta experiência."
                actionLabel="Voltar ao Descobrir"
                onActionPress={() =>
                  router.replace(
                    "/(tabs)/discover",
                  )
                }
                compact
              />
            )}
          </>
        ) : null}

        {step ===
        "time" ? (
          <>
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
                HORÁRIO
              </Text>

              <Text
                style={
                  styles.title
                }
              >
                Qual horário funciona para você?
              </Text>

              <Text
                style={
                  styles.description
                }
              >
                {
                  selectedDateLabel
                }
              </Text>
            </View>

            {selectedDay &&
            selectedDay.slots
              .length >
              0 ? (
              <View
                style={
                  styles.timeGrid
                }
              >
                {selectedDay.slots.map(
                  (slot) => {
                    const selected =
                      selectedSlotId ===
                      slot.id;
                    const label =
                      formatSlotTime(
                        slot.startsAt,
                        timezone,
                      );

                    return (
                      <Pressable
                        key={
                          slot.id
                        }
                        accessibilityRole="button"
                        accessibilityLabel={
                          `Horário ${label}`
                        }
                        accessibilityState={{
                          selected,
                        }}
                        onPress={() => {
                          setSelectedSlotId(
                            slot.id,
                          );

                          Haptics
                            .selectionAsync()
                            .catch(
                              () => {},
                            );
                        }}
                        style={({
                          pressed,
                        }) => [
                          styles.timeButton,
                          selected &&
                            styles.timeButtonSelected,
                          pressed &&
                            styles.pressed,
                        ]}
                      >
                        <Icon
                          name="clock"
                          size={14}
                          color={
                            selected
                              ? colors.onBrandPrimary
                              : colors.plum
                          }
                        />

                        <Text
                          style={[
                            styles.timeText,
                            selected &&
                              styles.timeTextSelected,
                          ]}
                        >
                          {label}
                        </Text>
                      </Pressable>
                    );
                  },
                )}
              </View>
            ) : (
              <EmptyState
                title="Sem horários neste dia"
                description="Escolha outra data disponível."
                actionLabel="Trocar data"
                onActionPress={() =>
                  setStep(
                    "date",
                  )
                }
                compact
              />
            )}
          </>
        ) : null}

        {step ===
        "confirm" &&
        booking ? (
          <>
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
                CONFIRMAÇÃO
              </Text>

              <Text
                style={
                  styles.title
                }
              >
                Seu horário está temporariamente reservado.
              </Text>

              <Text
                style={
                  styles.description
                }
              >
                {holdExpiration
                  ? `Confirme até ${holdExpiration} para garantir este horário.`
                  : "Confirme agora para garantir este horário."}
              </Text>
            </View>

            <View
              style={
                styles.confirmCard
              }
            >
              <View
                style={
                  styles.confirmRow
                }
              >
                <Icon
                  name="calendar"
                  size={18}
                  color={
                    colors.plum
                  }
                />

                <View
                  style={
                    styles.confirmContent
                  }
                >
                  <Text
                    style={
                      styles.confirmLabel
                    }
                  >
                    Data
                  </Text>

                  <Text
                    style={
                      styles.confirmValue
                    }
                  >
                    {
                      formatDayCard(
                        booking.slot.localDate,
                      ).label
                    }
                  </Text>
                </View>
              </View>

              <View
                style={
                  styles.confirmDivider
                }
              />

              <View
                style={
                  styles.confirmRow
                }
              >
                <Icon
                  name="clock"
                  size={18}
                  color={
                    colors.plum
                  }
                />

                <View
                  style={
                    styles.confirmContent
                  }
                >
                  <Text
                    style={
                      styles.confirmLabel
                    }
                  >
                    Horário
                  </Text>

                  <Text
                    style={
                      styles.confirmValue
                    }
                  >
                    {
                      booking.slot.localTime
                    }
                    {" · "}
                    {
                      formatDuration(
                        booking
                          .experience
                          .durationMinutes,
                      )
                    }
                  </Text>
                </View>
              </View>

              <View
                style={
                  styles.confirmDivider
                }
              />

              <View
                style={
                  styles.confirmRow
                }
              >
                <Icon
                  name="user"
                  size={18}
                  color={
                    colors.plum
                  }
                />

                <View
                  style={
                    styles.confirmContent
                  }
                >
                  <Text
                    style={
                      styles.confirmLabel
                    }
                  >
                    Profissional
                  </Text>

                  <Text
                    style={
                      styles.confirmValue
                    }
                  >
                    {
                      booking
                        .professional
                        .name
                    }
                  </Text>
                </View>
              </View>
            </View>

            <View
              style={
                styles.priceSummary
              }
            >
              <Text
                style={
                  styles.priceSummaryLabel
                }
              >
                Valor da experiência
              </Text>

              <Text
                style={
                  styles.priceSummaryValue
                }
              >
                {
                  formatCurrency(
                    booking.price,
                  )
                }
              </Text>
            </View>
          </>
        ) : null}

        {step ===
        "success" &&
        booking ? (
          <View
            style={
              styles.success
            }
          >
            <View
              style={
                styles.successIcon
              }
            >
              <Icon
                name="check"
                size={28}
                color={
                  colors.onBrandPrimary
                }
              />
            </View>

            <Text
              style={
                styles.successSpark
              }
            >
              {SPARK}
            </Text>

            <Text
              style={
                styles.successTitle
              }
            >
              Reserva confirmada.
            </Text>

            <Text
              style={
                styles.successDescription
              }
            >
              Seu horário está garantido no IDDUN.
            </Text>

            <View
              style={
                styles.successSummary
              }
            >
              <Text
                style={
                  styles.successService
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
                  styles.successDate
                }
              >
                {
                  formatDayCard(
                    booking.slot.localDate,
                  ).label
                }
              </Text>

              <Text
                style={
                  styles.successTime
                }
              >
                {
                  booking
                    .slot
                    .localTime
                }
              </Text>
            </View>

            <View
              style={
                styles.successButtons
              }
            >
              <Button
                title="Ver meus agendamentos"
                onPress={() =>
                  router.replace(
                    "/bookings",
                  )
                }
                fullWidth
              />

              <Button
                title="Descobrir mais experiências"
                onPress={() =>
                  router.replace(
                    "/(tabs)/discover",
                  )
                }
                variant="secondary"
                fullWidth
              />
            </View>
          </View>
        ) : null}

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>

      {step !==
        "success" &&
      availability.days.length >
        0 ? (
        <View
          style={
            styles.stickyBar
          }
        >
          <View
            style={
              styles.stickyPriceArea
            }
          >
            <Text
              style={
                styles.stickyLabel
              }
            >
              Valor
            </Text>

            <Text
              style={
                styles.stickyPrice
              }
            >
              {
                formatCurrency(
                  experience.price,
                )
              }
            </Text>
          </View>

          {step ===
          "confirm" ? (
            <Button
              title="Confirmar reserva"
              onPress={() => {
                void handleConfirm();
              }}
              loading={
                submitting
              }
              compact
            />
          ) : (
            <Button
              title={
                step === "date"
                  ? "Escolher horário"
                  : "Reservar horário"
              }
              onPress={() => {
                void handleContinue();
              }}
              disabled={
                step === "date"
                  ? !selectedDay
                  : !selectedSlot
              }
              loading={
                submitting
              }
              compact
            />
          )}
        </View>
      ) : null}
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

      loadingState: {
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
        paddingTop: 52,
        paddingHorizontal:
          spacing.lg,
        paddingBottom: 120,
      },

      headerOnly: {
        paddingTop: 54,
        paddingHorizontal:
          spacing.lg,
      },

      header: {
        minHeight:
          touch.minimum,
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

      headerCenter: {
        alignItems:
          "center",
      },

      headerTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 14,
      },

      headerStep: {
        marginTop: 2,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 9,
      },

      headerPlaceholder: {
        width:
          touch.minimum,
      },

      progress: {
        marginTop:
          spacing.lg,
        flexDirection:
          "row",
        gap: spacing.xs,
      },

      progressBar: {
        flex: 1,
        height: 3,
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.glassSoft,
      },

      progressBarActive: {
        backgroundColor:
          colors.plum,
      },

      experienceCard: {
        marginTop:
          spacing.xl,
        overflow:
          "hidden",
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      experienceImage: {
        width: 104,
        minHeight: 112,
      },

      experienceBody: {
        flex: 1,
        justifyContent:
          "center",
        padding:
          spacing.md,
      },

      experienceEyebrow: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        letterSpacing: 1,
      },

      experienceTitle: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 14,
        lineHeight: 18,
      },

      experienceMeta: {
        marginTop:
          spacing.xs,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 15,
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
        letterSpacing: 1.3,
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

      dateList: {
        paddingTop:
          spacing.xl,
        paddingRight:
          spacing.lg,
        gap: spacing.sm,
      },

      dateCard: {
        width: 76,
        minHeight: 98,
        padding:
          spacing.sm,
        borderRadius:
          radius.md,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      dateCardSelected: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },

      dateWeekday: {
        color:
          colors.muted,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        textTransform:
          "uppercase",
      },

      dateDay: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 28,
        lineHeight: 32,
      },

      dateMonth: {
        marginTop: 2,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 10,
      },

      dateTextSelected: {
        color:
          colors.onBrandPrimary,
      },

      timeGrid: {
        marginTop:
          spacing.xl,
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap: spacing.sm,
      },

      timeButton: {
        minWidth: 100,
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.lg,
        borderRadius:
          radius.pill,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.xs,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      timeButtonSelected: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },

      timeText: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansMedium,
        fontSize: 12,
      },

      timeTextSelected: {
        color:
          colors.onBrandPrimary,
      },

      confirmCard: {
        marginTop:
          spacing.xl,
        overflow:
          "hidden",
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      confirmRow: {
        minHeight: 74,
        padding:
          spacing.lg,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.md,
      },

      confirmContent: {
        flex: 1,
      },

      confirmLabel: {
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 9,
      },

      confirmValue: {
        marginTop: 3,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansMedium,
        fontSize: 13,
        lineHeight: 18,
      },

      confirmDivider: {
        height: 1,
        marginLeft: 50,
        backgroundColor:
          colors.glassBorder,
      },

      priceSummary: {
        marginTop:
          spacing.xl,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "space-between",
      },

      priceSummaryLabel: {
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 12,
      },

      priceSummaryValue: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 24,
      },

      success: {
        minHeight: 610,
        alignItems:
          "center",
        justifyContent:
          "center",
        paddingVertical:
          spacing.xxxl,
      },

      successIcon: {
        width: 72,
        height: 72,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plum,
      },

      successSpark: {
        marginTop:
          spacing.xl,
        color:
          colors.plum,
        fontFamily:
          fonts.display,
        fontSize: 16,
      },

      successTitle: {
        marginTop:
          spacing.sm,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 31,
        textAlign:
          "center",
      },

      successDescription: {
        marginTop:
          spacing.md,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        textAlign:
          "center",
      },

      successSummary: {
        width: "100%",
        marginTop:
          spacing.xxl,
        padding:
          spacing.xl,
        borderRadius:
          radius.md,
        alignItems:
          "center",
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      successService: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 15,
        textAlign:
          "center",
      },

      successDate: {
        marginTop:
          spacing.sm,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
      },

      successTime: {
        marginTop:
          spacing.sm,
        color:
          colors.plum,
        fontFamily:
          fonts.display,
        fontSize: 28,
      },

      successButtons: {
        width: "100%",
        marginTop:
          spacing.xxl,
        gap: spacing.sm,
      },

      stickyBar: {
        position:
          "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        minHeight: 88,
        paddingHorizontal:
          spacing.lg,
        paddingTop:
          spacing.md,
        paddingBottom: 22,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.md,
        backgroundColor:
          colors.overlayInkHeavy,
        borderTopWidth: 1,
        borderTopColor:
          colors.glassBorder,
      },

      stickyPriceArea: {
        flex: 1,
      },

      stickyLabel: {
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 9,
      },

      stickyPrice: {
        marginTop: 2,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 18,
      },

      bottomSpace: {
        height: 40,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );
