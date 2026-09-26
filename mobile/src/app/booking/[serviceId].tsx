import React, {
  useMemo,
  useState,
} from "react";
import {
  Alert,
  Linking,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import * as Haptics from "expo-haptics";

import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";

import {
  getProfessionalById,
  getServiceById,
} from "@/mocks/data";

import {
  useStoreVersion,
} from "@/store/local";

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

const WEB_CATALOG_URL =
  (process.env.EXPO_PUBLIC_WEB_URL ||
    "https://iddun-web.onrender.com"
  ).replace(/\/+$/, "") +
  "/experiencias";

type BookingDate = {
  date: Date;
  key: string;
  weekday: string;
  day: string;
  month: string;
  label: string;
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

  if (remaining === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remaining}min`;
}

function capitalize(
  value: string,
) {
  if (!value) {
    return value;
  }

  return (
    value.charAt(0).toUpperCase() +
    value.slice(1)
  );
}

function buildDates(
  count = 7,
): BookingDate[] {
  const today =
    new Date();

  today.setHours(
    12,
    0,
    0,
    0,
  );

  return Array.from(
    {
      length: count,
    },
    (_, index) => {
      const date =
        new Date(today);

      /*
       * IMPORTANTE:
       * index começa em 0.
       *
       * Portanto o primeiro dia
       * exibido é HOJE.
       */
      date.setDate(
        today.getDate() +
          index,
      );

      const weekday =
        new Intl.DateTimeFormat(
          "pt-BR",
          {
            weekday: "short",
          },
        )
          .format(date)
          .replace(".", "");

      const day =
        new Intl.DateTimeFormat(
          "pt-BR",
          {
            day: "2-digit",
          },
        ).format(date);

      const month =
        new Intl.DateTimeFormat(
          "pt-BR",
          {
            month: "short",
          },
        )
          .format(date)
          .replace(".", "");

      const fullLabel =
        capitalize(
          new Intl.DateTimeFormat(
            "pt-BR",
            {
              weekday: "long",
              day: "2-digit",
              month: "long",
            },
          ).format(date),
        );

      return {
        date,
        key: date
          .toISOString()
          .slice(0, 10),
        weekday:
          capitalize(
            weekday,
          ),
        day,
        month:
          capitalize(
            month,
          ),
        label:
          fullLabel,
      };
    },
  );
}

export default function BookingScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const params =
    useLocalSearchParams<{
      serviceId: string;
    }>();

  const service =
    getServiceById(
      params.serviceId,
    );

  const author =
    useMemo(
      () =>
        service
          ? getProfessionalById(
              service.authorId,
            )
          : undefined,
      [service],
    );

  const availableDates =
    useMemo(
      () =>
        buildDates(7),
      [],
    );

  const [step, setStep] =
    useState<BookingStep>(
      "date",
    );

  /*
   * Começa no primeiro item:
   * HOJE.
   *
   * No protótipo anterior
   * começava no índice 1,
   * ou seja, amanhã.
   */
  const [
    selectedDateKey,
    setSelectedDateKey,
  ] = useState(
    availableDates[0]?.key ??
      "",
  );

  const [
    selectedTime,
    setSelectedTime,
  ] =
    useState<string | null>(
      null,
    );

  const selectedDate =
    availableDates.find(
      (item) =>
        item.key ===
        selectedDateKey,
    );

  /*
   * Ainda é mock.
   *
   * Quando conectarmos ao Flask,
   * isso DEVE vir da API para
   * a data escolhida.
   */
  const availableTimes =
    useMemo(() => {
      if (!service) {
        return [];
      }

      return (
        service.availableSlots ??
        []
      );
    }, [service]);

  if (!service) {
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
          title="Serviço não encontrado"
          description="Não foi possível iniciar este agendamento."
          actionLabel="Descobrir"
          onActionPress={() =>
            router.replace(
              "/(tabs)/discover",
            )
          }
        />
      </View>
    );
  }

  const handleBack = () => {
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
      setStep("time");
      return;
    }

    if (
      step === "time"
    ) {
      setStep("date");
      return;
    }

    if (
      router.canGoBack()
    ) {
      router.back();
    } else {
      router.replace(
        `/service/${service.id}`,
      );
    }
  };

  const handleContinue =
    () => {
      Haptics.impactAsync(
        Haptics
          .ImpactFeedbackStyle
          .Light,
      ).catch(() => {});

      if (
        step === "date"
      ) {
        setStep("time");
        return;
      }

      if (
        step === "time"
      ) {
        if (!selectedTime) {
          return;
        }

        setStep(
          "confirm",
        );
      }
    };

  const handleConfirm =
    async () => {
      try {
        await Linking.openURL(
          WEB_CATALOG_URL,
        );
      } catch {
        Alert.alert(
          "Não foi possível abrir o site",
          "Acesse iddun-web.onrender.com/experiencias para consultar horários reais.",
        );
      }
    };

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
            onPress={
              handleBack
            }
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

        <View style={styles.loginWarning}>
          <Icon name="alert-circle" size={18} color={colors.plum} />
          <View style={styles.loginWarningContent}>
            <Text style={styles.loginWarningTitle}>
              Prévia de agendamento
            </Text>
            <Text style={styles.loginWarningText}>
              As datas, os horários e os preços aqui são ilustrativos. Consulte a disponibilidade real e reserve pelo site IDDUN.
            </Text>
          </View>
        </View>

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
                Selecione uma data para explorar a prévia. Os horários reais estão no site.
              </Text>
            </View>

            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={
                false
              }
              contentContainerStyle={
                styles.dateList
              }
            >
              {availableDates.map(
                (item) => {
                  const selected =
                    item.key ===
                    selectedDateKey;

                  return (
                    <Pressable
                      key={
                        item.key
                      }
                      accessibilityRole="button"
                      accessibilityLabel={
                        item.label
                      }
                      accessibilityState={{
                        selected,
                      }}
                      onPress={() => {
                        setSelectedDateKey(
                          item.key,
                        );

                        setSelectedTime(
                          null,
                        );

                        Haptics.selectionAsync().catch(
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
                          item.weekday
                        }
                      </Text>

                      <Text
                        style={[
                          styles.dateDay,

                          selected &&
                            styles.dateTextSelected,
                        ]}
                      >
                        {item.day}
                      </Text>

                      <Text
                        style={[
                          styles.dateMonth,

                          selected &&
                            styles.dateTextSelected,
                        ]}
                      >
                        {item.month}
                      </Text>
                    </Pressable>
                  );
                },
              )}
            </ScrollView>

            <View
              style={
                styles.summaryCard
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
                  styles.summaryCardContent
                }
              >
                <Text
                  style={
                    styles.summaryCardLabel
                  }
                >
                  Data selecionada
                </Text>

                <Text
                  style={
                    styles.summaryCardValue
                  }
                >
                  {selectedDate?.label ??
                    "Selecione uma data"}
                </Text>
              </View>
            </View>
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
                {selectedDate?.label}
              </Text>
            </View>

            {availableTimes.length >
            0 ? (
              <View
                style={
                  styles.timeGrid
                }
              >
                {availableTimes.map(
                  (time) => {
                    const selected =
                      selectedTime ===
                      time;

                    return (
                      <Pressable
                        key={
                          time
                        }
                        accessibilityRole="button"
                        accessibilityLabel={`Horário ${time}`}
                        accessibilityState={{
                          selected,
                        }}
                        onPress={() => {
                          setSelectedTime(
                            time,
                          );

                          Haptics.selectionAsync().catch(
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
                              ? colors
                                  .onBrandPrimary
                              : colors
                                  .plum
                          }
                        />

                        <Text
                          style={[
                            styles.timeText,

                            selected &&
                              styles.timeTextSelected,
                          ]}
                        >
                          {time}
                        </Text>
                      </Pressable>
                    );
                  },
                )}
              </View>
            ) : (
              <EmptyState
                title="Sem horários disponíveis"
                description="Não há horários disponíveis para esta data."
                actionLabel="Escolher outro dia"
                onActionPress={() =>
                  setStep(
                    "date",
                  )
                }
                compact
              />
            )}

            {selectedTime ? (
              <View
                style={
                  styles.summaryCard
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
                    styles.summaryCardContent
                  }
                >
                  <Text
                    style={
                      styles.summaryCardLabel
                    }
                  >
                    Horário selecionado
                  </Text>

                  <Text
                    style={
                      styles.summaryCardValue
                    }
                  >
                    {
                      selectedTime
                    }
                  </Text>
                </View>
              </View>
            ) : null}
          </>
        ) : null}

        {step ===
        "confirm" ? (
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
                PRÉVIA
              </Text>

              <Text
                style={
                  styles.title
                }
              >
                Confira os detalhes.
              </Text>

              <Text
                style={
                  styles.description
                }
              >
                Confira a prévia e consulte os horários reais no site.
              </Text>
            </View>

            <View
              style={
                styles.serviceCard
              }
            >
              {author ? (
                <Avatar
                  name={
                    author.name
                  }
                  uri={
                    author.avatar
                  }
                  size={54}
                />
              ) : (
                <View
                  style={
                    styles.serviceFallback
                  }
                >
                  <Icon
                    name="scissors"
                    size={20}
                    color={
                      colors.plum
                    }
                  />
                </View>
              )}

              <View
                style={
                  styles.serviceContent
                }
              >
                <Text
                  style={
                    styles.serviceName
                  }
                >
                  {service.name}
                </Text>

                {author ? (
                  <Text
                    style={
                      styles.serviceAuthor
                    }
                    numberOfLines={
                      1
                    }
                  >
                    {
                      author.name
                    }
                  </Text>
                ) : null}

                <Text
                  style={
                    styles.serviceMeta
                  }
                >
                  {formatDuration(
                    service.durationMinutes,
                  )}
                </Text>
              </View>
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
                <View
                  style={
                    styles.confirmIcon
                  }
                >
                  <Icon
                    name="calendar"
                    size={16}
                    color={
                      colors.plum
                    }
                  />
                </View>

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
                    {selectedDate?.label}
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
                <View
                  style={
                    styles.confirmIcon
                  }
                >
                  <Icon
                    name="clock"
                    size={16}
                    color={
                      colors.plum
                    }
                  />
                </View>

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
                    {selectedTime}
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
                <View
                  style={
                    styles.confirmIcon
                  }
                >
                  <Icon
                    name="map-pin"
                    size={16}
                    color={
                      colors.plum
                    }
                  />
                </View>

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
                    Local
                  </Text>

                  <Text
                    style={
                      styles.confirmValue
                    }
                  >
                    {
                      service.location
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
                Preço ilustrativo
              </Text>

              <Text
                style={
                  styles.priceSummaryValue
                }
              >
                {formatCurrency(
                  service.price,
                )}
              </Text>
            </View>
          </>
        ) : null}

        {step ===
        "success" ? (
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
                size={30}
                color={
                  colors.onBrandPrimary
                }
              />
            </View>

            <Text
              accessible={
                false
              }
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
              Prévia concluída.
            </Text>

            <Text
              style={
                styles.successDescription
              }
            >
              Consulte os horários reais no site IDDUN para fazer uma reserva.
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
                {service.name}
              </Text>

              <Text
                style={
                  styles.successDate
                }
              >
                {selectedDate?.label}
              </Text>

              <Text
                style={
                  styles.successTime
                }
              >
                {selectedTime}
              </Text>
            </View>

            <View
              style={
                styles.successButtons
              }
            >
              <Button
                title="Voltar ao início"
                onPress={() =>
                  router.replace(
                    "/(tabs)",
                  )
                }
                fullWidth
              />

              <Button
                title="Ver meu perfil"
                variant="secondary"
                onPress={() =>
                  router.replace(
                    "/(tabs)/profile",
                  )
                }
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
      "success" ? (
        <View
          style={
            styles.stickyBar
          }
        >
          {step ===
          "confirm" ? (
            <>
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
                  Preço ilustrativo
                </Text>

                <Text
                  style={
                    styles.stickyPrice
                  }
                >
                  {formatCurrency(
                    service.price,
                  )}
                </Text>
              </View>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Consultar horários reais no site"
                onPress={
                  handleConfirm
                }
                style={({
                  pressed,
                }) => [
                  styles.confirmButton,
                  pressed &&
                    styles.confirmButtonPressed,
                ]}
              >
                <Text
                  style={
                    styles.confirmButtonText
                  }
                >
                  Consultar no site
                </Text>

                <Icon
                  name="external-link"
                  size={15}
                  color={
                    colors
                      .onBrandPrimary
                  }
                />
              </Pressable>
            </>
          ) : (
            <Button
              title="Continuar"
              onPress={
                handleContinue
              }
              disabled={
                step ===
                  "time" &&
                !selectedTime
              }
              fullWidth
            />
          )}
        </View>
      ) : null}
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

    content: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
      paddingBottom: 110,
    },

    headerOnly: {
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

    headerCenter: {
      alignItems:
        "center",
    },

    headerTitle: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    headerStep: {
      marginTop: 2,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 9,
      lineHeight: 12,
    },

    headerPlaceholder: {
      width:
        touch.minimum,

      height:
        touch.minimum,
    },

    progress: {
      marginTop:
        spacing.lg,

      flexDirection:
        "row",

      gap: spacing.sm,
    },

    progressBar: {
      flex: 1,

      height: 3,

      borderRadius: 2,

      backgroundColor:
        colors.surfaceTertiary,
    },

    progressBarActive: {
      backgroundColor:
        colors.plum,
    },

    intro: {
      marginTop:
        spacing.xxxl,
    },

    eyebrow: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 14,

      letterSpacing: 1.5,
    },

    title: {
      maxWidth: 350,

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

    description: {
      maxWidth: 340,

      marginTop:
        spacing.md,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 13,
      lineHeight: 20,
    },

    dateList: {
      marginTop:
        spacing.xl,

      gap: spacing.sm,

      paddingRight:
        spacing.lg,
    },

    dateCard: {
      width: 74,
      minHeight: 104,

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

      fontSize: 10,
      lineHeight: 13,
    },

    dateDay: {
      marginTop: 4,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 24,
      lineHeight: 28,
    },

    dateMonth: {
      marginTop: 2,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 9,
      lineHeight: 12,
    },

    dateTextSelected: {
      color:
        colors.onBrandPrimary,
    },

    summaryCard: {
      marginTop:
        spacing.xl,

      minHeight: 68,

      padding:
        spacing.md,

      borderRadius:
        radius.md,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.md,

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    summaryCardContent: {
      flex: 1,
    },

    summaryCardLabel: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 9,
      lineHeight: 12,
    },

    summaryCardValue: {
      marginTop: 2,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansMedium,

      fontSize: 12,
      lineHeight: 16,
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
      minWidth: 96,

      minHeight:
        touch.minimum,

      paddingHorizontal:
        spacing.md,

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
      lineHeight: 16,
    },

    timeTextSelected: {
      color:
        colors.onBrandPrimary,
    },

    serviceCard: {
      marginTop:
        spacing.xl,

      minHeight: 84,

      padding:
        spacing.md,

      borderRadius:
        radius.md,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    serviceFallback: {
      width: 54,
      height: 54,

      borderRadius:
        radius.md,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.plumSoft,
    },

    serviceContent: {
      flex: 1,
      minWidth: 0,
    },

    serviceName: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 14,
      lineHeight: 18,
    },

    serviceAuthor: {
      marginTop: 2,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 14,
    },

    serviceMeta: {
      marginTop:
        spacing.xs,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 13,
    },

    confirmCard: {
      marginTop:
        spacing.lg,

      paddingHorizontal:
        spacing.md,

      borderRadius:
        radius.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    confirmRow: {
      minHeight: 72,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.md,
    },

    confirmIcon: {
      width: 38,
      height: 38,

      borderRadius:
        radius.md,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.plumSoft,
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
      lineHeight: 12,
    },

    confirmValue: {
      marginTop: 2,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansMedium,

      fontSize: 12,
      lineHeight: 17,
    },

    confirmDivider: {
      height: 1,

      marginLeft: 50,

      backgroundColor:
        colors.divider,
    },

    loginWarning: {
      marginTop:
        spacing.lg,

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
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    loginWarningContent: {
      flex: 1,
    },

    loginWarningTitle: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 12,
      lineHeight: 16,
    },

    loginWarningText: {
      marginTop:
        spacing.xs,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 16,
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
      lineHeight: 29,
    },

    success: {
      flex: 1,

      minHeight: 620,

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
      lineHeight: 20,
    },

    successTitle: {
      maxWidth: 330,

      marginTop:
        spacing.sm,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 31,
      lineHeight: 37,

      textAlign:
        "center",
    },

    successDescription: {
      maxWidth: 340,

      marginTop:
        spacing.md,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 12,
      lineHeight: 19,

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
      lineHeight: 19,
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
      lineHeight: 33,
    },

    successButtons: {
      width: "100%",

      marginTop:
        spacing.xxl,

      gap: spacing.sm,
    },

    stickyBar: {
      position: "absolute",

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
      lineHeight: 12,
    },

    stickyPrice: {
      marginTop: 2,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 18,
      lineHeight: 22,
    },

    confirmButton: {
      minHeight:
        touch.minimum,

      paddingHorizontal:
        spacing.xl,

      borderRadius:
        radius.pill,

      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "center",

      gap: spacing.sm,

      backgroundColor:
        colors.plum,
    },

    confirmButtonPressed: {
      opacity: 0.8,

      transform: [
        {
          scale: 0.98,
        },
      ],
    },

    confirmButtonText: {
      color:
        colors.onBrandPrimary,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    bottomSpace: {
      height: 40,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);
