import React, {
  useMemo,
  useState,
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
import { FavoriteButton } from "@/components/FavoriteButton";
import { Icon } from "@/components/Icon";
import { ProfessionalCard } from "@/components/ProfessionalCard";
import { ServiceCard } from "@/components/ServiceCard";

import {
  getPostAuthor,
  posts,
  professionals,
  services,
} from "@/mocks/data";

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

type FavoritesTab =
  | "posts"
  | "professionals"
  | "services";

const tabs: Array<{
  id: FavoritesTab;
  label: string;
}> = [
  {
    id: "posts",
    label: "Publicações",
  },
  {
    id: "professionals",
    label: "Profissionais",
  },
  {
    id: "services",
    label: "Serviços",
  },
];

export default function FavoritesScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [activeTab, setActiveTab] =
    useState<FavoritesTab>("posts");

  const favoritePostIds =
    store.favorites("posts");

  const favoriteProfessionalIds =
    store.favorites("professionals");

  const favoriteServiceIds =
    store.favorites("services");

  const favoritePosts =
    useMemo(
      () =>
        posts.filter((post) =>
          favoritePostIds.includes(
            post.id,
          ),
        ),
      [favoritePostIds],
    );

  const favoriteProfessionals =
    useMemo(
      () =>
        professionals.filter(
          (professional) =>
            favoriteProfessionalIds.includes(
              professional.id,
            ),
        ),
      [favoriteProfessionalIds],
    );

  const favoriteServices =
    useMemo(
      () =>
        services.filter((service) =>
          favoriteServiceIds.includes(
            service.id,
          ),
        ),
      [favoriteServiceIds],
    );

  const renderPosts = () => {
    if (
      favoritePosts.length === 0
    ) {
      return (
        <EmptyState
          title="Nenhuma publicação salva"
          description="Quando encontrar uma inspiração, toque no coração para guardar aqui."
          actionLabel="Descobrir"
          onActionPress={() =>
            router.push(
              "/(tabs)/discover",
            )
          }
        />
      );
    }

    return (
      <View
        style={
          styles.postGrid
        }
      >
        {favoritePosts.map(
          (post) => {
            const author =
              getPostAuthor(post);

            return (
              <Pressable
                key={post.id}
                accessibilityRole="button"
                accessibilityLabel={`Abrir publicação de ${author?.name ?? "profissional"}`}
                onPress={() =>
                  router.push(
                    `/post/${post.id}`,
                  )
                }
                style={({
                  pressed,
                }) => [
                  styles.postCard,
                  pressed &&
                    styles.pressed,
                ]}
              >
                <Image
                  source={{
                    uri: post.image,
                  }}
                  style={
                    styles.postImage
                  }
                  contentFit="cover"
                  transition={180}
                  accessibilityLabel={`Publicação de ${author?.name ?? "IDDUN"}`}
                />

                <View
                  style={
                    styles.postOverlay
                  }
                />

                <View
                  style={
                    styles.postFavorite
                  }
                >
                  <FavoriteButton
                    kind="posts"
                    id={post.id}
                    size={19}
                  />
                </View>

                <View
                  style={
                    styles.postContent
                  }
                >
                  <Text
                    style={
                      styles.postAuthor
                    }
                    numberOfLines={
                      1
                    }
                  >
                    {author?.name ??
                      "IDDUN"}
                  </Text>

                  <Text
                    style={
                      styles.postCaption
                    }
                    numberOfLines={
                      2
                    }
                  >
                    {post.caption}
                  </Text>
                </View>
              </Pressable>
            );
          },
        )}
      </View>
    );
  };

  const renderProfessionals =
    () => {
      if (
        favoriteProfessionals.length ===
        0
      ) {
        return (
          <EmptyState
            title="Nenhum profissional salvo"
            description="Favoritar um profissional é diferente de seguir. Salve aqui os perfis que você quer encontrar rapidamente."
            actionLabel="Explorar profissionais"
            onActionPress={() =>
              router.push(
                "/(tabs)/discover",
              )
            }
          />
        );
      }

      return (
        <View
          style={
            styles.list
          }
        >
          {favoriteProfessionals.map(
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
      );
    };

  const renderServices = () => {
    if (
      favoriteServices.length ===
      0
    ) {
      return (
        <EmptyState
          title="Nenhum serviço salvo"
          description="Salve os serviços que chamarem sua atenção para comparar e agendar depois."
          actionLabel="Explorar serviços"
          onActionPress={() =>
            router.push(
              "/(tabs)/discover",
            )
          }
        />
      );
    }

    return (
      <View
        style={
          styles.list
        }
      >
        {favoriteServices.map(
          (service) => {
            const author =
              professionals.find(
                (item) =>
                  item.id ===
                  service.authorId,
              );

            return (
              <ServiceCard
                key={
                  service.id
                }
                id={
                  service.id
                }
                name={
                  service.name
                }
                image={
                  service.image
                }
                category={
                  service.category
                }
                professionalName={
                  author?.name
                }
                location={
                  service.location
                }
                durationMinutes={
                  service.durationMinutes
                }
                price={
                  service.price
                }
                availableLabel={
                  service.availabilityLabel
                }
              />
            );
          },
        )}
      </View>
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
            accessibilityLabel="Descobrir"
            onPress={() =>
              router.push(
                "/(tabs)/discover",
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
              name="search"
              size={19}
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
            SUA CURADORIA
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Tudo o que você quis guardar.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Inspirações, profissionais e serviços reunidos em um só lugar.
          </Text>
        </View>

        <View
          style={
            styles.tabs
          }
        >
          {tabs.map(
            (tab) => {
              const selected =
                activeTab ===
                tab.id;

              return (
                <Pressable
                  key={
                    tab.id
                  }
                  accessibilityRole="button"
                  accessibilityState={{
                    selected,
                  }}
                  accessibilityLabel={
                    tab.label
                  }
                  onPress={() =>
                    setActiveTab(
                      tab.id,
                    )
                  }
                  style={({ pressed }) => [
                    styles.tab,

                    selected &&
                      styles.tabActive,

                    pressed &&
                      styles.pressed,
                  ]}
                >
                  <Text
                    style={[
                      styles.tabText,

                      selected &&
                        styles.tabTextActive,
                    ]}
                    numberOfLines={
                      1
                    }
                  >
                    {
                      tab.label
                    }
                  </Text>
                </Pressable>
              );
            },
          )}
        </View>

        <View
          style={
            styles.tabContent
          }
        >
          {activeTab ===
          "posts"
            ? renderPosts()
            : activeTab ===
                "professionals"
              ? renderProfessionals()
              : renderServices()}
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
        marginTop:
          spacing.xl,

        paddingHorizontal:
          spacing.lg,
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
        maxWidth: 340,

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

      tabs: {
        marginTop:
          spacing.xl,

        marginHorizontal:
          spacing.lg,

        padding: 4,

        minHeight: 48,

        borderRadius:
          radius.pill,

        flexDirection:
          "row",

        backgroundColor:
          colors.surfaceSecondary,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      tab: {
        flex: 1,

        minHeight: 40,

        paddingHorizontal:
          spacing.sm,

        borderRadius:
          radius.pill,

        alignItems:
          "center",

        justifyContent:
          "center",
      },

      tabActive: {
        backgroundColor:
          colors.surfaceTertiary,
      },

      tabText: {
        color:
          colors.muted,

        fontFamily:
          fonts.sansMedium,

        fontSize: 11,
        lineHeight: 15,
      },

      tabTextActive: {
        color:
          colors.onSurface,
      },

      tabContent: {
        marginTop:
          spacing.xl,

        paddingHorizontal:
          spacing.lg,
      },

      list: {
        gap: spacing.sm,
      },

      postGrid: {
        flexDirection:
          "row",

        flexWrap:
          "wrap",

        gap: spacing.sm,
      },

      postCard: {
        width:
          "48.5%",

        aspectRatio:
          0.78,

        position:
          "relative",

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

      postImage: {
        width:
          "100%",

        height:
          "100%",
      },

      postOverlay: {
        position:
          "absolute",

        left: 0,
        right: 0,
        top: 0,
        bottom: 0,

        backgroundColor:
          "rgba(11,11,15,0.22)",
      },

      postFavorite: {
        position:
          "absolute",

        top: 3,
        right: 3,
      },

      postContent: {
        position:
          "absolute",

        left:
          spacing.sm,

        right:
          spacing.sm,

        bottom:
          spacing.sm,
      },

      postAuthor: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 11,
        lineHeight: 14,
      },

      postCaption: {
        marginTop: 2,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sans,

        fontSize: 9,
        lineHeight: 13,
      },

      bottomSpace: {
        height: 120,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );