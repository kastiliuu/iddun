import React, {
  useEffect,
  useState,
} from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import {
  getBeautyGraph,
  getSavedItems,
  type SavedItemsResponse,
} from "@/api/graph";

import { EmptyState } from "@/components/EmptyState";
import { FavoriteButton } from "@/components/FavoriteButton";
import { Icon } from "@/components/Icon";
import { ProfessionalCard } from "@/components/ProfessionalCard";
import { ServiceCard } from "@/components/ServiceCard";

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

const tabs: {
  id: FavoritesTab;
  label: string;
}[] = [
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

const emptySavedItems: SavedItemsResponse = {
  profiles: [],
  experiences: [],
  posts: [],
  portfolioItems: [],
};

export default function FavoritesScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [activeTab, setActiveTab] =
    useState<FavoritesTab>("posts");

  const [saved, setSaved] =
    useState<SavedItemsResponse>(
      emptySavedItems,
    );

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(
      null,
    );

  const user =
    store.getUser();

  useEffect(() => {
    let mounted = true;

    const load =
      async () => {
        if (!user) {
          if (mounted) {
            setSaved(
              emptySavedItems,
            );
            setError(
              null,
            );
            setLoading(
              false,
            );
          }

          return;
        }

        try {
          if (mounted) {
            setLoading(
              true,
            );
          }

          const [
            response,
            graph,
          ] = await Promise.all([
            getSavedItems(),
            getBeautyGraph(),
          ]);

          if (!mounted) {
            return;
          }

          store.replaceGraphState(
            graph,
          );

          setSaved(
            response,
          );
          setError(
            null,
          );
        } catch (loadError) {
          if (!mounted) {
            return;
          }

          setSaved(
            emptySavedItems,
          );
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Não foi possível carregar seus salvos.",
          );
        } finally {
          if (mounted) {
            setLoading(
              false,
            );
          }
        }
      };

    void load();

    return () => {
      mounted = false;
    };
  }, [user?.id]);

  const visiblePosts =
    saved.posts.filter(
      (post) =>
        store.isGraphSaved(
          "work_post",
          Number(post.id),
        ),
    );

  const visiblePortfolio =
    saved.portfolioItems.filter(
      (item) =>
        store.isGraphSaved(
          "portfolio_item",
          Number(item.id),
        ),
    );

  const visibleProfiles =
    saved.profiles.filter(
      (profile) =>
        store.isGraphSaved(
          profile.kind,
          Number(profile.id),
        ),
    );

  const visibleExperiences =
    saved.experiences.filter(
      (experience) =>
        store.isGraphSaved(
          "experience",
          experience.entityId,
        ),
    );

  const renderPublications = () => {
    if (
      visiblePosts.length === 0 &&
      visiblePortfolio.length === 0
    ) {
      return (
        <EmptyState
          title="Nenhuma publicação salva"
          description="Quando encontrar uma inspiração real no IDDUN, toque no coração para guardar aqui."
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
        {visiblePosts.map(
          (post) => (
            <Pressable
              key={
                `post-${post.id}`
              }
              accessibilityRole="button"
              accessibilityLabel={
                `Abrir publicação de ${post.author.name}`
              }
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
                accessibilityLabel={
                  `Publicação de ${post.author.name}`
                }
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
                  targetId={
                    Number(
                      post.id,
                    )
                  }
                  targetType="work_post"
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
                  numberOfLines={1}
                >
                  {
                    post.author.name
                  }
                </Text>

                <Text
                  style={
                    styles.postCaption
                  }
                  numberOfLines={2}
                >
                  {
                    post.caption ||
                    "Trabalho publicado no IDDUN"
                  }
                </Text>
              </View>
            </Pressable>
          ),
        )}

        {visiblePortfolio.map(
          (item) => (
            <Pressable
              key={
                `portfolio-${item.id}`
              }
              accessibilityRole="button"
              accessibilityLabel={
                `Abrir perfil de ${item.authorName}`
              }
              onPress={() =>
                router.push(
                  `/professional/${item.professionalRouteId}`,
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
                  uri: item.image,
                }}
                style={
                  styles.postImage
                }
                contentFit="cover"
                transition={180}
                accessibilityLabel={
                  `Trabalho de ${item.authorName}`
                }
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
                  id={item.id}
                  targetId={
                    Number(
                      item.id,
                    )
                  }
                  targetType="portfolio_item"
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
                  numberOfLines={1}
                >
                  {
                    item.authorName
                  }
                </Text>

                <Text
                  style={
                    styles.postCaption
                  }
                  numberOfLines={2}
                >
                  {
                    item.caption ||
                    "Portfólio profissional"
                  }
                </Text>
              </View>
            </Pressable>
          ),
        )}
      </View>
    );
  };

  const renderProfessionals =
    () => {
      if (
        visibleProfiles.length ===
        0
      ) {
        return (
          <EmptyState
            title="Nenhum perfil salvo"
            description="Salve profissionais e estabelecimentos para encontrá-los rapidamente."
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
          {visibleProfiles.map(
            (profile) => (
              <View
                key={
                  `${profile.kind}-${profile.id}`
                }
                style={
                  styles.profileSavedWrap
                }
              >
                <ProfessionalCard
                  id={
                    profile.id
                  }
                  routeId={
                    profile.routeId
                  }
                  name={
                    profile.name
                  }
                  avatar={
                    profile.avatar
                  }
                  specialty={
                    profile.specialty ??
                    undefined
                  }
                  location={
                    profile.location ??
                    undefined
                  }
                  rating={
                    profile.rating ??
                    undefined
                  }
                  reviewsCount={
                    profile.reviewsCount
                  }
                  routeType={
                    profile.kind
                  }
                  showFollow={false}
                />

                <View
                  style={
                    styles.profileFavorite
                  }
                >
                  <FavoriteButton
                    kind="professionals"
                    id={
                      profile.id
                    }
                    targetId={
                      Number(
                        profile.id,
                      )
                    }
                    targetType={
                      profile.kind
                    }
                    size={20}
                  />
                </View>
              </View>
            ),
          )}
        </View>
      );
    };

  const renderServices = () => {
    if (
      visibleExperiences.length ===
      0
    ) {
      return (
        <EmptyState
          title="Nenhuma experiência salva"
          description="Salve experiências reais para comparar e agendar depois."
          actionLabel="Explorar experiências"
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
        {visibleExperiences.map(
          (experience) => (
            <ServiceCard
              key={
                experience.entityId
              }
              id={
                experience.id
              }
              targetId={
                experience.entityId
              }
              name={
                experience.name
              }
              image={
                experience.image
              }
              category={
                experience.category ??
                undefined
              }
              professionalName={
                experience.professionalName ??
                undefined
              }
              location={
                experience.location ??
                undefined
              }
              durationMinutes={
                experience.durationMinutes
              }
              price={
                experience.price
              }
            />
          ),
        )}
      </View>
    );
  };

  const renderContent = () => {
    if (!user) {
      return (
        <EmptyState
          title="Entre para ver seus salvos"
          description="Os salvos reais ficam vinculados à sua conta para aparecerem em todos os seus dispositivos."
          actionLabel="Entrar"
          onActionPress={() =>
            router.push(
              "/login",
            )
          }
        />
      );
    }

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
            Carregando seus salvos...
          </Text>
        </View>
      );
    }

    if (error) {
      return (
        <EmptyState
          title="Não foi possível carregar"
          description={error}
          actionLabel="Descobrir"
          onActionPress={() =>
            router.push(
              "/(tabs)/discover",
            )
          }
        />
      );
    }

    if (
      activeTab ===
      "posts"
    ) {
      return renderPublications();
    }

    if (
      activeTab ===
      "professionals"
    ) {
      return renderProfessionals();
    }

    return renderServices();
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
            Publicações, perfis e experiências reais reunidos em um só lugar.
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
                    numberOfLines={1}
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
          {
            renderContent()
          }
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
        gap:
          spacing.sm,
      },

      profileSavedWrap: {
        position:
          "relative",
      },

      profileFavorite: {
        position:
          "absolute",
        right:
          spacing.sm,
        top:
          spacing.sm,
        zIndex: 2,
      },

      postGrid: {
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap:
          spacing.sm,
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

      loadingState: {
        minHeight: 260,
        alignItems:
          "center",
        justifyContent:
          "center",
        gap:
          spacing.md,
      },

      loadingText: {
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 12,
      },

      bottomSpace: {
        height: 120,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );
