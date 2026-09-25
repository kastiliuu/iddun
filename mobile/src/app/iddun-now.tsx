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
import { IDDUNNowCard } from "@/components/IDDUNNowCard";
import { Icon } from "@/components/Icon";

import {
  getIDDUNNowData,
  iddunNowItems,
} from "@/mocks/data";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type NowFilter =
  | "all"
  | "today"
  | "soon";

const filters: Array<{
  id: NowFilter;
  label: string;
}> = [
  {
    id: "all",
    label: "Todos",
  },
  {
    id: "today",
    label: "Hoje",
  },
  {
    id: "soon",
    label: "Em breve",
  },
];

export default function IDDUNNowScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [filter, setFilter] =
    React.useState<NowFilter>("all");

  const items =
    useMemo(() => {
      const hydrated =
        iddunNowItems
          .map((item) =>
            getIDDUNNowData(
              item,
            ),
          )
          .filter(Boolean) as Array<
          NonNullable<
            ReturnType<
              typeof getIDDUNNowData
            >
          >
        >;

      if (filter === "all") {
        return hydrated;
      }

      if (filter === "today") {
        return hydrated.filter(
          ({ item }) =>
            item.timeLabel
              .toLowerCase()
              .startsWith(
                "hoje",
              ),
        );
      }

      return hydrated.filter(
        ({ item }) =>
          !item.timeLabel
            .toLowerCase()
            .startsWith(
              "hoje",
            ),
      );
    }, [filter]);

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
            styles.hero
          }
        >
          <View
            style={
              styles.eyebrowRow
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
            O horário certo pode aparecer agora.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Descubra disponibilidades que acabaram de abrir com profissionais e espaços no IDDUN.
          </Text>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={
            false
          }
          contentContainerStyle={
            styles.filters
          }
        >
          {filters.map(
            (item) => {
              const active =
                filter ===
                item.id;

              return (
                <Pressable
                  key={
                    item.id
                  }
                  accessibilityRole="button"
                  accessibilityState={{
                    selected:
                      active,
                  }}
                  onPress={() =>
                    setFilter(
                      item.id,
                    )
                  }
                  style={({
                    pressed,
                  }) => [
                    styles.filterButton,

                    active &&
                      styles.filterButtonActive,

                    pressed &&
                      styles.pressed,
                  ]}
                >
                  <Text
                    style={[
                      styles.filterText,

                      active &&
                        styles.filterTextActive,
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
        </ScrollView>

        <View
          style={
            styles.resultHeader
          }
        >
          <Text
            style={
              styles.resultTitle
            }
          >
            Disponíveis agora
          </Text>

          <Text
            style={
              styles.resultCount
            }
          >
            {items.length}
          </Text>
        </View>

        {items.length >
        0 ? (
          <View
            style={
              styles.list
            }
          >
            {items.map(
              ({
                item,
                service,
                professional,
              }) => (
                <View
                  key={
                    item.id
                  }
                  style={
                    styles.cardWrap
                  }
                >
                  <IDDUNNowCard
                    serviceId={
                      service.id
                    }
                    professionalId={
                      professional.id
                    }
                    professionalName={
                      professional.name
                    }
                    professionalAvatar={
                      professional.avatar
                    }
                    serviceName={
                      service.name
                    }
                    image={
                      service.image
                    }
                    price={
                      service.price
                    }
                    timeLabel={
                      item.timeLabel
                    }
                    location={
                      service.location
                    }
                    routeType={
                      professional.kind
                    }
                    urgent={
                      item.urgent
                    }
                  />
                </View>
              ),
            )}
          </View>
        ) : (
          <EmptyState
            title="Nenhum horário agora"
            description="Novas disponibilidades podem aparecer a qualquer momento."
            actionLabel="Descobrir profissionais"
            onActionPress={() =>
              router.push(
                "/(tabs)/discover",
              )
            }
          />
        )}

        <View
          style={
            styles.infoCard
          }
        >
          <Icon
            name="bell"
            size={20}
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
              Siga quem você gosta
            </Text>

            <Text
              style={
                styles.infoText
              }
            >
              O IDDUN pode avisar quando um profissional que você acompanha abrir um novo horário.
            </Text>
          </View>
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

      headerButtonPlaceholder: {
        width:
          touch.minimum,

        height:
          touch.minimum,
      },

      logo: {
        width: 104,
        height: 32,
      },

      hero: {
        marginTop:
          spacing.xl,
      },

      eyebrowRow: {
        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,
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

        fontSize: 34,
        lineHeight: 40,

        letterSpacing: -0.5,
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

      filters: {
        marginTop:
          spacing.xl,

        gap: spacing.sm,
      },

      filterButton: {
        minHeight:
          touch.minimum,

        paddingHorizontal:
          spacing.lg,

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

      filterButtonActive: {
        backgroundColor:
          colors.plum,

        borderColor:
          colors.plum,
      },

      filterText: {
        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sansMedium,

        fontSize: 12,
        lineHeight: 16,
      },

      filterTextActive: {
        color:
          colors.onBrandPrimary,
      },

      resultHeader: {
        marginTop:
          spacing.xxl,

        flexDirection:
          "row",

        alignItems:
          "center",

        justifyContent:
          "space-between",
      },

      resultTitle: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 23,
        lineHeight: 29,
      },

      resultCount: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 13,
        lineHeight: 17,
      },

      list: {
        marginTop:
          spacing.lg,

        gap: spacing.lg,
      },

      cardWrap: {
        alignItems:
          "center",
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

      infoContent: {
        flex: 1,
      },

      infoTitle: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 13,
        lineHeight: 17,
      },

      infoText: {
        marginTop:
          spacing.xs,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sans,

        fontSize: 11,
        lineHeight: 17,
      },

      bottomSpace: {
        height: 60,
      },

      pressed: {
        opacity: 0.75,
      },
    }),
  );