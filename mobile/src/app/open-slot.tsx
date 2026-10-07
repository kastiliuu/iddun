import React, {
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ActivityIndicator,
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

import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toast";

import {
  createAvailability,
  getAvailabilityOptions,
  type AvailabilityOption,
} from "@/api/availability";

import {
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

type DateOption = {
  key: string;
  label: string;
  weekday: string;
  day: string;
  month: string;
};

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
): DateOption[] {
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

      const label =
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

      const year =
        date.getFullYear();

      const monthNumber =
        String(
          date.getMonth() + 1,
        ).padStart(2, "0");

      const dayNumber =
        String(
          date.getDate(),
        ).padStart(2, "0");

      return {
        key:
          `${year}-${monthNumber}-${dayNumber}`,

        label,

        weekday:
          capitalize(
            weekday,
          ),

        day,

        month:
          capitalize(
            month,
          ),
      };
    },
  );
}

const defaultTimes = [
  "09:00",
  "09:30",
  "10:00",
  "10:30",
  "11:00",
  "11:30",
  "12:00",
  "13:00",
  "13:30",
  "14:00",
  "14:30",
  "15:00",
  "15:30",
  "16:00",
  "16:30",
  "17:00",
  "17:30",
  "18:00",
];

export default function OpenSlotScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const params =
    useLocalSearchParams<{
      serviceId?: string;
    }>();

  const user =
    store.getUser();

  const canManage =
    user?.role ===
      "professional" ||
    user?.role ===
      "establishment";

  const [
    services,
    setServices,
  ] = useState<
    AvailabilityOption[]
  >([]);

  const [
    optionsLoading,
    setOptionsLoading,
  ] = useState(true);

  const [
    optionsError,
    setOptionsError,
  ] = useState<
    string | null
  >(null);

  const [serviceId, setServiceId] =
    useState(
      params.serviceId ??
        "",
    );

  useEffect(() => {
    let mounted = true;

    const loadOptions =
      async () => {
        if (!canManage) {
          setOptionsLoading(false);
          return;
        }

        try {
          const response =
            await getAvailabilityOptions();

          if (!mounted) {
            return;
          }

          setServices(
            response.items,
          );

          setServiceId(
            (current) =>
              current ||
              response.items[0]?.id ||
              "",
          );

          setOptionsError(
            null,
          );
        } catch (error) {
          if (!mounted) {
            return;
          }

          setServices([]);
          setOptionsError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar seus serviços.",
          );
        } finally {
          if (mounted) {
            setOptionsLoading(
              false,
            );
          }
        }
      };

    void loadOptions();

    return () => {
      mounted = false;
    };
  }, [canManage]);

  const dates =
    useMemo(
      () => buildDates(7),
      [],
    );

  const [
    selectedDate,
    setSelectedDate,
  ] =
    useState(
      dates[0]?.key ??
        "",
    );

  const [
    selectedTime,
    setSelectedTime,
  ] =
    useState<string | null>(
      null,
    );

  const [loading, setLoading] =
    useState(false);

  const selectedService =
    services.find(
      (service) =>
        service.id ===
        serviceId,
    );

  const selectedDateInfo =
    dates.find(
      (date) =>
        date.key ===
        selectedDate,
    );

  const canSubmit =
    Boolean(
      serviceId &&
        selectedDate &&
        selectedTime,
    );

  const handleSubmit =
    async () => {
      if (
        !canSubmit ||
        !selectedTime
      ) {
        toast.show({
          title:
            "Escolha o horário",
          body:
            "Selecione serviço, data e horário antes de publicar.",
          icon:
            "alert-circle",
        });

        return;
      }

      try {
        setLoading(true);

        await createAvailability({
          serviceId,

          date:
            selectedDate,

          time:
            selectedTime,

          cutoffMinutes:
            null,
        });

        Haptics.notificationAsync(
          Haptics
            .NotificationFeedbackType
            .Success,
        ).catch(() => {});

        toast.show({
          title:
            "Horário publicado",
          body:
            "A disponibilidade foi publicada e pode aparecer no IDDUN Now.",
          icon:
            "check",
        });

        router.replace(
          "/iddun-now",
        );
      } catch (error) {
        toast.show({
          title:
            "Não foi possível abrir o horário",
          body:
            error instanceof Error
              ? error.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setLoading(false);
      }
    };

  if (!user || !canManage) {
    return (
      <View
        style={
          styles.container
        }
      >
        <View
          style={
            styles.simpleHeader
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
                  "/(tabs)/create",
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

        <View
          style={
            styles.restricted
          }
        >
          <View
            style={
              styles.restrictedIcon
            }
          >
            <Icon
              name="clock"
              size={26}
              color={
                colors.plum
              }
            />
          </View>

          <Text
            style={
              styles.restrictedTitle
            }
          >
            Área profissional
          </Text>

          <Text
            style={
              styles.restrictedText
            }
          >
            Apenas profissionais e estabelecimentos podem publicar disponibilidades.
          </Text>

          <Button
            title="Voltar"
            variant="secondary"
            onPress={() =>
              router.replace(
                "/(tabs)/create",
              )
            }
            fullWidth
          />
        </View>
      </View>
    );
  }

  if (optionsLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.loadingState}>
          <ActivityIndicator
            color={colors.plum}
          />
          <Text style={styles.loadingText}>
            Carregando seus serviços...
          </Text>
        </View>
      </View>
    );
  }

  if (optionsError) {
    return (
      <View style={styles.container}>
        <EmptyState
          title="Serviços indisponíveis"
          description={optionsError}
          actionLabel="Voltar"
          onActionPress={() =>
            router.replace(
              "/(tabs)/create",
            )
          }
        />
      </View>
    );
  }

  if (services.length === 0) {
    return (
      <View style={styles.container}>
        <EmptyState
          title="Nenhum serviço publicado"
          description="Publique um serviço antes de abrir uma disponibilidade."
          actionLabel="Voltar"
          onActionPress={() =>
            router.replace(
              "/(tabs)/create",
            )
          }
        />
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
        keyboardShouldPersistTaps="handled"
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
                  "/manage-services",
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
            Abrir horário
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
          <View
            style={
              styles.liveRow
            }
          >
            <View
              style={
                styles.liveDot
              }
            />

            <Text
              style={
                styles.eyebrow
              }
            >
              IDDUN NOW
            </Text>
          </View>

          <Text
            style={
              styles.title
            }
          >
            Transforme um horário livre em oportunidade.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Publique uma disponibilidade para que clientes encontrem um atendimento no momento certo.
          </Text>
        </View>

        <View
          style={
            styles.section
          }
        >
          <Text
            style={
              styles.sectionLabel
            }
          >
            1. SERVIÇO
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            O que será oferecido?
          </Text>

          {services.length >
          0 ? (
            <View
              style={
                styles.serviceList
              }
            >
              {services.map(
                (service) => {
                  const selected =
                    service.id ===
                    serviceId;

                  return (
                    <Pressable
                      key={
                        service.id
                      }
                      accessibilityRole="button"
                      accessibilityState={{
                        selected,
                      }}
                      onPress={() => {
                        setServiceId(
                          service.id,
                        );

                        Haptics.selectionAsync().catch(
                          () => {},
                        );
                      }}
                      style={({
                        pressed,
                      }) => [
                        styles.serviceCard,

                        selected &&
                          styles.serviceCardSelected,

                        pressed &&
                          styles.pressed,
                      ]}
                    >
                      <View
                        style={
                          styles.serviceIcon
                        }
                      >
                        <Icon
                          name="scissors"
                          size={18}
                          color={
                            selected
                              ? colors
                                  .plum
                              : colors
                                  .muted
                          }
                        />
                      </View>

                      <View
                        style={
                          styles.serviceContent
                        }
                      >
                        <Text
                          style={
                            styles.serviceName
                          }
                          numberOfLines={
                            1
                          }
                        >
                          {
                            service.name
                          }
                        </Text>

                        <Text
                          style={
                            styles.serviceCategory
                          }
                        >
                          {
                            service.category
                          }
                        </Text>
                      </View>

                      {selected ? (
                        <View
                          style={
                            styles.selectedCheck
                          }
                        >
                          <Icon
                            name="check"
                            size={13}
                            color={
                              colors
                                .onBrandPrimary
                            }
                          />
                        </View>
                      ) : null}
                    </Pressable>
                  );
                },
              )}
            </View>
          ) : (
            <View
              style={
                styles.emptyService
              }
            >
              <Text
                style={
                  styles.emptyServiceText
                }
              >
                Você precisa cadastrar um serviço antes de abrir horários.
              </Text>

              <Button
                title="Cadastrar serviço"
                variant="secondary"
                onPress={() =>
                  router.push(
                    "/create-service",
                  )
                }
                fullWidth
              />
            </View>
          )}
        </View>

        <View
          style={
            styles.section
          }
        >
          <Text
            style={
              styles.sectionLabel
            }
          >
            2. DATA
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            Para qual dia?
          </Text>

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={
              false
            }
            contentContainerStyle={
              styles.dateList
            }
          >
            {dates.map(
              (date) => {
                const selected =
                  selectedDate ===
                  date.key;

                return (
                  <Pressable
                    key={
                      date.key
                    }
                    accessibilityRole="button"
                    accessibilityState={{
                      selected,
                    }}
                    accessibilityLabel={
                      date.label
                    }
                    onPress={() => {
                      setSelectedDate(
                        date.key,
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
                          styles.dateSelectedText,
                      ]}
                    >
                      {
                        date.weekday
                      }
                    </Text>

                    <Text
                      style={[
                        styles.dateDay,

                        selected &&
                          styles.dateSelectedText,
                      ]}
                    >
                      {date.day}
                    </Text>

                    <Text
                      style={[
                        styles.dateMonth,

                        selected &&
                          styles.dateSelectedText,
                      ]}
                    >
                      {date.month}
                    </Text>
                  </Pressable>
                );
              },
            )}
          </ScrollView>
        </View>

        <View
          style={
            styles.section
          }
        >
          <Text
            style={
              styles.sectionLabel
            }
          >
            3. HORÁRIO
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            Qual horário ficou livre?
          </Text>

          <View
            style={
              styles.timeGrid
            }
          >
            {defaultTimes.map(
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
        </View>

        <View
          style={
            styles.section
          }
        >
          <Text
            style={
              styles.sectionLabel
            }
          >
            4. CONFIRMAÇÃO
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            Revise os dados antes de publicar.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Horários dentro das próximas 24 horas recebem destaque automático como oportunidade recente no IDDUN Now.
          </Text>
        </View>

        {selectedService &&
        selectedTime ? (
          <View
            style={
              styles.preview
            }
          >
            <Text
              style={
                styles.previewEyebrow
              }
            >
              PRÉVIA
            </Text>

            <View
              style={
                styles.previewCard
              }
            >
              <View
                style={
                  styles.previewTop
                }
              >
                <View>
                  <Text
                    style={
                      styles.previewNow
                    }
                  >
                    DISPONIBILIDADE
                  </Text>

                  <Text
                    style={
                      styles.previewService
                    }
                  >
                    {
                      selectedService.name
                    }
                  </Text>
                </View>

                <View
                  style={
                    styles.previewTimeBadge
                  }
                >
                  <Icon
                    name="clock"
                    size={12}
                    color={
                      colors.plum
                    }
                  />

                  <Text
                    style={
                      styles.previewTime
                    }
                  >
                    {
                      selectedTime
                    }
                  </Text>
                </View>
              </View>

              <Text
                style={
                  styles.previewDate
                }
              >
                {
                  selectedDateInfo?.label
                }
              </Text>

            </View>
          </View>
        ) : null}

        <View
          style={
            styles.infoCard
          }
        >
          <Icon
            name="shield"
            size={18}
            color={
              colors.plum
            }
          />

          <View
            style={
              styles.infoContent
            }
          >
            <Text
              style={
                styles.infoTitle
              }
            >
              O backend ainda confirma a disponibilidade
            </Text>

            <Text
              style={
                styles.infoText
              }
            >
              Ao publicar, o servidor deve verificar conflitos e regras de agenda antes de liberar o horário.
            </Text>
          </View>
        </View>

        <View
          style={
            styles.submit
          }
        >
          <Button
            title="Publicar disponibilidade"
            onPress={
              handleSubmit
            }
            disabled={
              !canSubmit
            }
            loading={
              loading
            }
            fullWidth
          />
        </View>

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

      simpleHeader: {
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
        fontSize: 13,
      },

      headerPlaceholder: {
        width:
          touch.minimum,
        height:
          touch.minimum,
      },

      intro: {
        marginTop:
          spacing.xl,
      },

      liveRow: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.sm,
      },

      liveDot: {
        width: 7,
        height: 7,
        borderRadius: 4,
        backgroundColor:
          colors.plum,
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

      section: {
        marginTop:
          spacing.xxxl,
      },

      sectionLabel: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        lineHeight: 12,
        letterSpacing: 1.2,
      },

      sectionTitle: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 22,
        lineHeight: 28,
      },

      serviceList: {
        marginTop:
          spacing.lg,
        gap:
          spacing.sm,
      },

      serviceCard: {
        minHeight: 72,
        padding:
          spacing.md,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      serviceCardSelected: {
        backgroundColor:
          colors.plumSoft,
        borderColor:
          colors.plum,
      },

      serviceIcon: {
        width: 40,
        height: 40,
        borderRadius:
          radius.md,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.glassSoft,
      },

      serviceContent: {
        flex: 1,
      },

      serviceName: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 13,
      },

      serviceCategory: {
        marginTop: 2,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
      },

      selectedCheck: {
        width: 26,
        height: 26,
        borderRadius: 13,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plum,
      },

      emptyService: {
        marginTop:
          spacing.lg,
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

      emptyServiceText: {
        marginBottom:
          spacing.lg,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 11,
        lineHeight: 17,
      },

      dateList: {
        marginTop:
          spacing.lg,
        gap:
          spacing.sm,
      },

      dateCard: {
        width: 72,
        minHeight: 98,
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
      },

      dateDay: {
        marginTop: 4,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 23,
      },

      dateMonth: {
        marginTop: 2,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 9,
      },

      dateSelectedText: {
        color:
          colors.onBrandPrimary,
      },

      timeGrid: {
        marginTop:
          spacing.lg,
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap:
          spacing.sm,
      },

      timeButton: {
        minWidth: 82,
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.pill,
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

      timeButtonSelected: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },

      timeText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },

      timeTextSelected: {
        color:
          colors.onBrandPrimary,
      },

      nowCard: {
        marginTop:
          spacing.lg,
        padding:
          spacing.lg,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      nowCardActive: {
        backgroundColor:
          colors.plumSoft,
        borderColor:
          colors.plum,
      },

      nowIcon: {
        width: 44,
        height: 44,
        borderRadius:
          radius.md,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.glassSoft,
      },

      nowContent: {
        flex: 1,
      },

      nowTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 13,
      },

      nowDescription: {
        marginTop: 3,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 15,
      },

      switchTrack: {
        width: 46,
        height: 26,
        padding: 3,
        borderRadius: 13,
        justifyContent:
          "center",
        backgroundColor:
          colors.surfaceTertiary,
      },

      switchTrackActive: {
        backgroundColor:
          colors.plum,
      },

      switchThumb: {
        width: 20,
        height: 20,
        borderRadius: 10,
        backgroundColor:
          colors.onSurfaceSecondary,
      },

      switchThumbActive: {
        alignSelf:
          "flex-end",
        backgroundColor:
          colors.onBrandPrimary,
      },

      noteInput: {
        minHeight: 110,
        marginTop:
          spacing.lg,
        padding:
          spacing.md,
        borderRadius:
          radius.md,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 18,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      counter: {
        alignSelf:
          "flex-end",
        marginTop:
          spacing.xs,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 9,
      },

      preview: {
        marginTop:
          spacing.xxxl,
      },

      previewEyebrow: {
        marginBottom:
          spacing.sm,
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        letterSpacing: 1.2,
      },

      previewCard: {
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

      previewTop: {
        flexDirection:
          "row",
        alignItems:
          "flex-start",
        justifyContent:
          "space-between",
        gap:
          spacing.md,
      },

      previewNow: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        letterSpacing: 1,
      },

      previewService: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 21,
      },

      previewTimeBadge: {
        paddingHorizontal:
          spacing.sm,
        paddingVertical: 6,
        borderRadius:
          radius.pill,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.xs,
        backgroundColor:
          colors.plumSoft,
      },

      previewTime: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 11,
      },

      previewDate: {
        marginTop:
          spacing.md,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 11,
      },

      previewNote: {
        marginTop:
          spacing.sm,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 16,
      },

      infoCard: {
        marginTop:
          spacing.xxl,
        padding:
          spacing.lg,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "flex-start",
        gap:
          spacing.md,
        backgroundColor:
          colors.plumSoft,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      infoContent: {
        flex: 1,
      },

      infoTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 12,
        lineHeight: 16,
      },

      infoText: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 16,
      },

      submit: {
        marginTop:
          spacing.xxl,
      },

      restricted: {
        marginTop: 150,
        paddingHorizontal:
          spacing.lg,
        alignItems:
          "center",
      },

      restrictedIcon: {
        width: 64,
        height: 64,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plumSoft,
      },

      restrictedTitle: {
        marginTop:
          spacing.lg,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 26,
      },

      restrictedText: {
        maxWidth: 320,
        marginTop:
          spacing.sm,
        marginBottom:
          spacing.xl,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 18,
        textAlign:
          "center",
      },

      loadingState: {
        flex: 1,
        minHeight: 320,
        alignItems: "center",
        justifyContent: "center",
        gap: spacing.md,
        paddingHorizontal: spacing.lg,
      },

      loadingText: {
        color: colors.muted,
        fontFamily: fonts.sans,
        fontSize: 12,
      },

      bottomSpace: {
        height: 72,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );