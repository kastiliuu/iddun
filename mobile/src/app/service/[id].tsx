import React, {
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ActivityIndicator,
  Pressable,
  Share,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { API_URL } from "@/api/client";
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";

import { Avatar } from "@/components/Avatar";
import { EmptyState } from "@/components/EmptyState";
import { FavoriteButton } from "@/components/FavoriteButton";
import { Icon } from "@/components/Icon";
import { Rating } from "@/components/Rating";

import type {
  Service,
} from "@/mocks/data";

import {
  getRealExperience,
  type CatalogExperience,
} from "@/api/experiences";

import {
  getProfessional,
  type ProfessionalProfileResponse,
} from "@/api/professionals";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

function formatDuration(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(
    minutes / 60,
  );

  const remaining =
    minutes % 60;

  if (remaining === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remaining}min`;
}

export default function ServiceDetailScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const params =
    useLocalSearchParams<{
      id: string;
    }>();

  const [
    remoteExperience,
    setRemoteExperience,
  ] =
    useState<CatalogExperience | null>(
      null,
    );

  const [
    remoteAuthor,
    setRemoteAuthor,
  ] =
    useState<ProfessionalProfileResponse | null>(
      null,
    );

  const [
    remoteLoading,
    setRemoteLoading,
  ] =
    useState(true);

  useEffect(
    () => {
      let mounted =
        true;

      getRealExperience(
        params.id,
      )
        .then(
          async (
            experience,
          ) => {
            if (!mounted) {
              return;
            }

            setRemoteExperience(
              experience,
            );

            try {
              const profile =
                await getProfessional(
                  experience
                    .professionalSlug,
                );

              if (mounted) {
                setRemoteAuthor(
                  profile,
                );
              }
            } catch {
              if (mounted) {
                setRemoteAuthor(
                  null,
                );
              }
            }
          },
        )
        .catch(
          () => {
            if (mounted) {
              setRemoteExperience(
                null,
              );
            }
          },
        )
        .finally(
          () => {
            if (mounted) {
              setRemoteLoading(
                false,
              );
            }
          },
        );

      return () => {
        mounted = false;
      };
    },
    [
      params.id,
    ],
  );

  const service =
    useMemo<Service | undefined>(
      () => {
        if (!remoteExperience) {
          return undefined;
        }

        return {
          id:
            remoteExperience.slug,
          entityId:
            remoteExperience.entityId,
          authorId:
            remoteAuthor
              ?.professional.id ??
            remoteExperience
              .professionalSlug,
          authorRouteId:
            remoteExperience
              .professionalSlug,
          authorKind:
            "professional",
          name:
            remoteExperience.title,
          category:
            remoteExperience.category,
          description:
            remoteExperience
              .description,
          image:
            remoteExperience.imageUrl,
          durationMinutes:
            remoteExperience
              .durationMinutes,
          price:
            remoteExperience.price,
          location:
            remoteExperience.location,
          availabilityLabel:
            remoteExperience
              .availableSlotsCount >
            0
              ? (
                  remoteExperience
                    .availableSlotsCount
                  + " horários disponíveis"
                )
              : "Novos horários em breve",
          availableSlots: [],
        };
      },
      [
        remoteExperience,
        remoteAuthor,
      ],
    );

  const author =
    remoteAuthor
      ?.professional;

  if (
    remoteLoading &&
    !service
  ) {
    return (
      <View
        style={
          styles.loading
        }
        accessibilityRole="progressbar"
        accessibilityLabel="Carregando serviço"
      >
        <ActivityIndicator
          color={
            colors.plum
          }
        />
      </View>
    );
  }

  if (!service) {
    return (
      <View
        style={
          styles.container
        }
      >
        <View
          style={
            styles.notFoundHeader
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
          description="Esse serviço não está disponível no momento."
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

  const openAuthor = () => {
    if (!author) {
      return;
    }

    router.push(
      author.kind ===
        "establishment"
        ? `/establishment/${author.routeId ?? author.id}`
        : `/professional/${author.routeId ?? service.authorRouteId ?? author.id}`,
    );
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
            styles.hero
          }
        >
          <Image
            source={{
              uri: service.image,
            }}
            style={
              styles.heroImage
            }
            contentFit="cover"
            transition={220}
            accessibilityLabel={`Imagem do serviço ${service.name}`}
          />

          <View
            style={
              styles.heroOverlay
            }
          />

          <View
            style={
              styles.topActions
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

            <View
              style={
                styles.topRightActions
              }
            >
              <FavoriteButton
                kind="services"
                id={service.id}
                targetId={
                  service.entityId ??
                  undefined
                }
              />

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Compartilhar serviço"
                onPress={() => {
                  void Share.share({
                    message:
                      `Veja ${service.name} no IDDUN: ${API_URL}/experiencias/${service.id}`,
                  });
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
                  name="share-2"
                  size={18}
                  color={
                    colors.onSurface
                  }
                />
              </Pressable>
            </View>
          </View>
        </View>

        <View
          style={
            styles.main
          }
        >
          <Text
            style={
              styles.category
            }
          >
            {service.category.toUpperCase()}
          </Text>

          <Text
            style={
              styles.title
            }
          >
            {service.name}
          </Text>

          <View
            style={
              styles.infoRow
            }
          >
            <View
              style={
                styles.infoItem
              }
            >
              <Icon
                name="clock"
                size={14}
                color={
                  colors.plum
                }
              />

              <Text
                style={
                  styles.infoText
                }
              >
                {formatDuration(
                  service.durationMinutes,
                )}
              </Text>
            </View>

            <View
              style={
                styles.infoSeparator
              }
            />

            <View
              style={
                styles.infoItem
              }
            >
              <Icon
                name="map-pin"
                size={14}
                color={
                  colors.plum
                }
              />

              <Text
                style={
                  styles.infoText
                }
                numberOfLines={1}
              >
                {
                  service.location
                }
              </Text>
            </View>
          </View>

          <Text
            style={
              styles.description
            }
          >
            {service.description}
          </Text>

          {author ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Abrir perfil de ${author.name}`}
              onPress={
                openAuthor
              }
              style={({
                pressed,
              }) => [
                styles.authorCard,
                pressed &&
                  styles.pressed,
              ]}
            >
              <Avatar
                name={
                  author.name
                }
                uri={
                  author.avatar
                }
                size={54}
              />

              <View
                style={
                  styles.authorContent
                }
              >
                <Text
                  style={
                    styles.authorEyebrow
                  }
                >
                  {author.kind ===
                  "establishment"
                    ? "ESTABELECIMENTO"
                    : "PROFISSIONAL"}
                </Text>

                <Text
                  style={
                    styles.authorName
                  }
                  numberOfLines={1}
                >
                  {author.name}
                </Text>

                <View
                  style={
                    styles.authorMeta
                  }
                >
                  <Rating
                    value={
                      author.rating
                    }
                    small
                  />

                  <Text
                    style={
                      styles.authorReviews
                    }
                  >
                    {
                      author.reviewsCount
                    }{" "}
                    avaliações
                  </Text>
                </View>
              </View>

              <Icon
                name="chevron-right"
                size={18}
                color={
                  colors.muted
                }
              />
            </Pressable>
          ) : null}

          <View
            style={
              styles.section
            }
          >
            <Text
              style={
                styles.sectionEyebrow
              }
            >
              DISPONIBILIDADE
            </Text>

            <Text
              style={
                styles.sectionTitle
              }
            >
              Próximos horários
            </Text>

            {service.availableSlots &&
            service.availableSlots.length >
              0 ? (
              <View
                style={
                  styles.slots
                }
              >
                {service.availableSlots.map(
                  (slot) => (
                    <Pressable
                      key={
                        slot
                      }
                      accessibilityRole="button"
                      accessibilityLabel={`Agendar às ${slot}`}
                      onPress={() =>
                        router.push(
                          `/booking/${service.id}`,
                        )
                      }
                      style={({
                        pressed,
                      }) => [
                        styles.slot,
                        pressed &&
                          styles.slotPressed,
                      ]}
                    >
                      <Icon
                        name="clock"
                        size={13}
                        color={
                          colors.plum
                        }
                      />

                      <Text
                        style={
                          styles.slotText
                        }
                      >
                        {slot}
                      </Text>
                    </Pressable>
                  ),
                )}
              </View>
            ) : (
              <Text
                style={
                  styles.noSlots
                }
              >
                Consulte a agenda para ver os próximos horários disponíveis.
              </Text>
            )}
          </View>

          <View
            style={
              styles.infoCard
            }
          >
            <Icon
              name="shield"
              size={19}
              color={
                colors.plum
              }
            />

            <View
              style={
                styles.infoCardContent
              }
            >
              <Text
                style={
                  styles.infoCardTitle
                }
              >
                Agendamento pelo IDDUN
              </Text>

              <Text
                style={
                  styles.infoCardText
                }
              >
                A disponibilidade final será confirmada pela agenda do profissional ou estabelecimento antes da conclusão.
              </Text>
            </View>
          </View>

          <View
            style={
              styles.bottomSpace
            }
          />
        </View>
      </ScrollView>

      <View
        style={
          styles.stickyBar
        }
      >
        <View
          style={
            styles.priceArea
          }
        >
          <Text
            style={
              styles.priceLabel
            }
          >
            Valor
          </Text>

          <Text
            style={
              styles.price
            }
          >
            {formatCurrency(
              service.price,
            )}
          </Text>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Agendar ${service.name}`}
          onPress={() =>
            router.push(
              `/booking/${service.id}`,
            )
          }
          style={({
            pressed,
          }) => [
            styles.bookButton,
            pressed &&
              styles.bookButtonPressed,
          ]}
        >
          <Text
            style={
              styles.bookButtonText
            }
          >
            Agendar
          </Text>

          <Icon
            name="arrow-right"
            size={15}
            color={
              colors.onBrandPrimary
            }
          />
        </Pressable>
      </View>
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

    loading: {
      flex: 1,
      alignItems:
        "center",
      justifyContent:
        "center",
      backgroundColor:
        colors.surface,
    },

    content: {
      paddingBottom: 100,
    },

    notFoundHeader: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
    },

    hero: {
      width: "100%",
      height: 390,

      position: "relative",

      backgroundColor:
        colors.surfaceTertiary,
    },

    heroImage: {
      width: "100%",
      height: "100%",
    },

    heroOverlay: {
      position: "absolute",

      top: 0,
      right: 0,
      bottom: 0,
      left: 0,

      backgroundColor:
        colors.overlayInkSoft,
    },

    topActions: {
      position: "absolute",

      top: 54,
      left: spacing.lg,
      right: spacing.lg,

      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "space-between",
    },

    topRightActions: {
      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.xs,
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
        colors.overlayInk,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    main: {
      paddingHorizontal:
        spacing.lg,

      paddingTop:
        spacing.xl,
    },

    category: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 14,

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

      fontSize: 32,
      lineHeight: 38,

      letterSpacing: -0.4,
    },

    infoRow: {
      marginTop:
        spacing.lg,

      flexDirection:
        "row",

      alignItems:
        "center",

      flexWrap:
        "wrap",

      gap: spacing.sm,
    },

    infoItem: {
      minWidth: 0,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.xs,
    },

    infoSeparator: {
      width: 3,
      height: 3,

      borderRadius: 2,

      backgroundColor:
        colors.muted,
    },

    infoText: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 12,
      lineHeight: 16,
    },

    description: {
      marginTop:
        spacing.xl,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 13,
      lineHeight: 21,
    },

    authorCard: {
      minHeight: 82,

      marginTop:
        spacing.xxl,

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

    authorContent: {
      flex: 1,
      minWidth: 0,
    },

    authorEyebrow: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 8,
      lineHeight: 11,

      letterSpacing: 0.8,
    },

    authorName: {
      marginTop: 2,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 14,
      lineHeight: 18,
    },

    authorMeta: {
      marginTop:
        spacing.xs,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,
    },

    authorReviews: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 13,
    },

    section: {
      marginTop:
        spacing.xxxl,
    },

    sectionEyebrow: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 9,
      lineHeight: 12,

      letterSpacing: 1.3,
    },

    sectionTitle: {
      marginTop:
        spacing.xs,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 24,
      lineHeight: 30,
    },

    slots: {
      marginTop:
        spacing.lg,

      flexDirection:
        "row",

      flexWrap:
        "wrap",

      gap: spacing.sm,
    },

    slot: {
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
        colors.glassSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    slotPressed: {
      backgroundColor:
        colors.plumSoft,

      borderColor:
        colors.plum,
    },

    slotText: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansMedium,

      fontSize: 12,
      lineHeight: 16,
    },

    noSlots: {
      marginTop:
        spacing.md,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 12,
      lineHeight: 18,
    },

    infoCard: {
      marginTop:
        spacing.xxxl,

      padding:
        spacing.lg,

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

    infoCardContent: {
      flex: 1,
    },

    infoCardTitle: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    infoCardText: {
      marginTop:
        spacing.xs,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 17,
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

    priceArea: {
      flex: 1,
    },

    priceLabel: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 9,
      lineHeight: 12,
    },

    price: {
      marginTop: 2,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 18,
      lineHeight: 22,
    },

    bookButton: {
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

    bookButtonPressed: {
      opacity: 0.8,

      transform: [
        {
          scale: 0.98,
        },
      ],
    },

    bookButtonText: {
      color:
        colors.onBrandPrimary,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    bottomSpace: {
      height: 48,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);