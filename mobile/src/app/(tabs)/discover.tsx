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
  TextInput,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import { CategoryChip } from "@/components/CategoryChip";
import { DiscoverTile } from "@/components/DiscoverTile";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { ProfessionalCard } from "@/components/ProfessionalCard";
import { SectionHeader } from "@/components/SectionHeader";
import {
  getRealExperiences,
  type CatalogExperience,
} from "@/api/experiences";

import {
  categories,
  discoverItems,
  professionals,
} from "@/mocks/data";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

const CATEGORY_CODES: Record<string, string> = {
  Unhas: "unhas",
  Cabelo: "cabelo",
  Barbearia: "barbearia",
  Tatuagem: "tatuagem",
  Sobrancelhas: "sobrancelhas",
  Estética: "estetica",
};

export default function DiscoverScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [search, setSearch] =
    useState("");

  const [selectedCategory, setSelectedCategory] =
    useState("Todos");

  const [realExperiences, setRealExperiences] =
    useState<CatalogExperience[]>([]);
  const [realLoading, setRealLoading] =
    useState(true);
  const [realError, setRealError] =
    useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setRealLoading(true);
      getRealExperiences(
        {
          search,
          category: CATEGORY_CODES[selectedCategory],
        },
        controller.signal,
      )
        .then((response) => {
          setRealExperiences(response.items);
          setRealError(false);
        })
        .catch((error: unknown) => {
          if (
            error instanceof Error &&
            error.name === "AbortError"
          ) {
            return;
          }
          setRealExperiences([]);
          setRealError(true);
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setRealLoading(false);
          }
        });
    }, 250);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search, selectedCategory]);

  const openRealExperience = (
    experience: CatalogExperience,
  ) => {
    router.push(
      `/booking/${experience.slug}`,
    );
  };

  const filteredItems =
    useMemo(() => {
      const normalizedSearch =
        search
          .trim()
          .toLowerCase();

      return discoverItems.filter(
        (item) => {
          const matchesCategory =
            selectedCategory ===
              "Todos" ||
            item.category ===
              selectedCategory;

          const matchesSearch =
            !normalizedSearch ||
            item.title
              .toLowerCase()
              .includes(
                normalizedSearch,
              ) ||
            item.subtitle
              ?.toLowerCase()
              .includes(
                normalizedSearch,
              ) ||
            item.location
              ?.toLowerCase()
              .includes(
                normalizedSearch,
              );

          return (
            matchesCategory &&
            matchesSearch
          );
        },
      );
    }, [
      search,
      selectedCategory,
    ]);

  const leftColumn =
    filteredItems.filter(
      (_, index) =>
        index % 2 === 0,
    );

  const rightColumn =
    filteredItems.filter(
      (_, index) =>
        index % 2 !== 0,
    );

  const nearbyProfessionals =
    useMemo(
      () =>
        professionals.slice(
          0,
          4,
        ),
      [],
    );

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
          <Image
            source={require(
              "../../../assets/branding/iddun-logo-white.png",
            )}
            style={
              styles.logo
            }
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Notificações"
            onPress={() =>
              router.push(
                "/notifications",
              )
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
              name="bell"
              size={20}
              color={
                colors.onSurface
              }
            />
          </Pressable>
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
            DESCOBRIR
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Encontre algo que você ainda não sabia que queria.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Explore estilos, profissionais, serviços e espaços em um só lugar.
          </Text>
        </View>

        <View
          style={
            styles.searchWrap
          }
        >
          <Icon
            name="search"
            size={18}
            color={
              colors.muted
            }
          />

          <TextInput
            value={search}
            onChangeText={
              setSearch
            }
            placeholder="Busque estilo, serviço ou profissional"
            placeholderTextColor={
              colors.muted
            }
            autoCorrect={false}
            returnKeyType="search"
            style={
              styles.searchInput
            }
            accessibilityLabel="Buscar no IDDUN"
          />

          {search.length >
          0 ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Limpar busca"
              hitSlop={8}
              onPress={() =>
                setSearch("")
              }
              style={
                styles.clearButton
              }
            >
              <Icon
                name="x"
                size={17}
                color={
                  colors.onSurfaceSecondary
                }
              />
            </Pressable>
          ) : null}
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={
            false
          }
          contentContainerStyle={
            styles.categories
          }
        >
          {categories.map(
            (category) => (
              <CategoryChip
                key={
                  category
                }
                label={
                  category
                }
                selected={
                  selectedCategory ===
                  category
                }
                onPress={() =>
                  setSelectedCategory(
                    category,
                  )
                }
              />
            ),
          )}
        </ScrollView>

        <View style={styles.sectionHeaderWrap}>
          <SectionHeader
            title="Experiências publicadas"
            subtitle="Disponibilidade e preços do catálogo IDDUN"
          />
        </View>

        <View style={styles.realList}>
          {realLoading ? (
            <ActivityIndicator color={colors.plum} />
          ) : realError ? (
            <Text style={styles.realMessage}>
              Não foi possível carregar o catálogo agora. Tente novamente em instantes.
            </Text>
          ) : realExperiences.length === 0 ? (
            <Text style={styles.realMessage}>
              Nenhuma experiência publicada corresponde à busca.
            </Text>
          ) : (
            realExperiences.map((experience) => (
              <Pressable
                key={experience.id}
                accessibilityRole="button"
                accessibilityLabel={`Agendar ${experience.title}`}
                onPress={() => {
                  openRealExperience(experience);
                }}
                style={styles.realCard}
              >
                <Image
                  source={{ uri: experience.imageUrl }}
                  style={styles.realImage}
                  contentFit="cover"
                  accessibilityLabel={experience.title}
                />
                <View style={styles.realDetails}>
                  <Text style={styles.realTitle} numberOfLines={2}>
                    {experience.title}
                  </Text>
                  <Text style={styles.realMessage} numberOfLines={1}>
                    {experience.professional} · {experience.location}
                  </Text>
                  <Text style={styles.realPrice}>
                    {new Intl.NumberFormat("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    }).format(experience.price)}
                  </Text>
                  <Text style={styles.realMessage}>
                    {experience.availableSlotsCount > 0
                      ? `${experience.availableSlotsCount} horário(s) disponível(is)`
                      : "Sem horários no momento"}
                  </Text>
                </View>
              </Pressable>
            ))
          )}
        </View>

        <View
          style={
            styles.sectionHeaderWrap
          }
        >
          <SectionHeader
            title={
              selectedCategory ===
                "Todos"
                ? "Inspiração visual"
                : selectedCategory
            }
            subtitle={
              search
                ? `Resultados para "${search}"`
                : "Prévia de estilos e perfis; dados ilustrativos"
            }
          />
        </View>

        {filteredItems.length >
        0 ? (
          <View
            style={
              styles.masonry
            }
          >
            <View
              style={
                styles.column
              }
            >
              {leftColumn.map(
                (item) => (
                  <DiscoverTile
                    key={
                      item.id
                    }
                    id={
                      item.sourceId
                    }
                    type={
                      item.type
                    }
                    title={
                      item.title
                    }
                    subtitle={
                      item.subtitle
                    }
                    image={
                      item.image
                    }
                    rating={
                      item.rating
                    }
                    location={
                      item.location
                    }
                    height={
                      item.height
                    }
                  />
                ),
              )}
            </View>

            <View
              style={
                styles.column
              }
            >
              {rightColumn.map(
                (item) => (
                  <DiscoverTile
                    key={
                      item.id
                    }
                    id={
                      item.sourceId
                    }
                    type={
                      item.type
                    }
                    title={
                      item.title
                    }
                    subtitle={
                      item.subtitle
                    }
                    image={
                      item.image
                    }
                    rating={
                      item.rating
                    }
                    location={
                      item.location
                    }
                    height={
                      item.height
                    }
                  />
                ),
              )}
            </View>
          </View>
        ) : (
          <EmptyState
            title="Sem inspirações nesta categoria"
            description="Confira as experiências publicadas acima ou tente outro filtro."
            actionLabel="Limpar filtros"
            onActionPress={() => {
              setSearch("");
              setSelectedCategory(
                "Todos",
              );
            }}
          />
        )}

        {!search &&
        selectedCategory ===
          "Todos" ? (
          <View
            style={
              styles.nearbySection
            }
          >
            <SectionHeader
              title="Perfis de exemplo"
              subtitle="Prévia visual do IDDUN"
              actionLabel="Ver mais"
              onActionPress={() => {}}
            />

            <View
              style={
                styles.professionalsList
              }
            >
              {nearbyProfessionals.map(
                (
                  professional,
                ) => (
                  <ProfessionalCard
                    key={
                      professional.id
                    }
                    id={
                      professional.id
                    }
                    name={
                      professional.name
                    }
                    avatar={
                      professional.avatar
                    }
                    specialty={
                      professional.specialty
                    }
                    location={
                      professional.location
                    }
                    rating={
                      professional.rating
                    }
                    reviewsCount={
                      professional.reviewsCount
                    }
                    routeType={
                      professional.kind
                    }
                  />
                ),
              )}
            </View>
          </View>
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

      content: {
        paddingTop: 54,
      },

      header: {
        minHeight: 52,

        paddingHorizontal:
          spacing.lg,

        flexDirection:
          "row",

        alignItems:
          "center",

        justifyContent:
          "space-between",
      },

      logo: {
        width: 112,
        height: 34,
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

      intro: {
        paddingHorizontal:
          spacing.lg,

        marginTop:
          spacing.xl,
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
        maxWidth: 330,

        marginTop:
          spacing.md,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sans,

        fontSize: 13,
        lineHeight: 19,
      },

      searchWrap: {
        minHeight: 52,

        marginTop:
          spacing.xl,

        marginHorizontal:
          spacing.lg,

        paddingHorizontal:
          spacing.md,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,

        borderRadius:
          radius.md,

        backgroundColor:
          colors.surfaceSecondary,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      searchInput: {
        flex: 1,

        paddingVertical:
          spacing.md,

        color:
          colors.onSurface,

        fontFamily:
          fonts.sans,

        fontSize: 13,
        lineHeight: 18,
      },

      clearButton: {
        width:
          touch.minimum,

        height:
          touch.minimum,

        alignItems:
          "center",

        justifyContent:
          "center",
      },

      categories: {
        paddingHorizontal:
          spacing.lg,

        paddingTop:
          spacing.lg,

        gap: spacing.sm,
      },

      locationRow: {
        minHeight: 44,

        marginTop:
          spacing.md,

        marginHorizontal:
          spacing.lg,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,
      },

      locationText: {
        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sansMedium,

        fontSize: 12,
        lineHeight: 16,
      },

      locationAction: {
        marginLeft: "auto",

        minHeight: 36,

        justifyContent:
          "center",
      },

      locationActionText: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 11,
      },

      sectionHeaderWrap: {
        marginTop:
          spacing.xl,

        paddingHorizontal:
          spacing.lg,
      },

      realList: {
        marginTop: spacing.md,
        paddingHorizontal: spacing.lg,
        gap: spacing.sm,
      },

      realCard: {
        minHeight: 116,
        flexDirection: "row",
        overflow: "hidden",
        borderRadius: radius.md,
        backgroundColor: colors.surfaceSecondary,
        borderWidth: 1,
        borderColor: colors.glassBorder,
      },

      realImage: {
        width: 112,
        minHeight: 116,
      },

      realDetails: {
        flex: 1,
        justifyContent: "center",
        padding: spacing.md,
        gap: spacing.xs,
      },

      realTitle: {
        color: colors.onSurface,
        fontFamily: fonts.sansSemiBold,
        fontSize: 14,
      },

      realMessage: {
        color: colors.onSurfaceSecondary,
        fontFamily: fonts.sans,
        fontSize: 12,
        lineHeight: 18,
      },

      realPrice: {
        color: colors.onSurface,
        fontFamily: fonts.sansSemiBold,
        fontSize: 13,
      },

      masonry: {
        marginTop:
          spacing.lg,

        paddingHorizontal:
          spacing.lg,

        flexDirection:
          "row",

        alignItems:
          "flex-start",

        gap: spacing.sm,
      },

      column: {
        flex: 1,

        gap: spacing.sm,
      },

      nearbySection: {
        marginTop:
          spacing.xxxl,

        paddingHorizontal:
          spacing.lg,

        gap: spacing.lg,
      },

      professionalsList: {
        gap: spacing.sm,
      },

      bottomSpace: {
        height: 120,
      },

      pressed: {
        opacity: 0.75,
      },
    }),
  );
