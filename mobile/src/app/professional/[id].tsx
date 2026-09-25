import React, {
  useMemo,
  useRef,
  useState,
} from "react";
import {
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
import { BottomSheetModal } from "@gorhom/bottom-sheet";

import { Avatar } from "@/components/Avatar";
import { CommentsSheet } from "@/components/CommentsSheet";
import { EmptyState } from "@/components/EmptyState";
import { FavoriteButton } from "@/components/FavoriteButton";
import { FollowButton } from "@/components/FollowButton";
import { Icon } from "@/components/Icon";
import { PostCard } from "@/components/PostCard";
import { Rating } from "@/components/Rating";
import { ServiceCard } from "@/components/ServiceCard";

import {
  getPostService,
  getPostsByAuthorId,
  getProfessionalById,
  getServicesByAuthorId,
} from "@/mocks/data";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type ProfileTab =
  | "work"
  | "services"
  | "reviews";

const tabs: Array<{
  id: ProfileTab;
  label: string;
}> = [
  {
    id: "work",
    label: "Trabalhos",
  },
  {
    id: "services",
    label: "Serviços",
  },
  {
    id: "reviews",
    label: "Avaliações",
  },
];

export default function ProfessionalProfileScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const params =
    useLocalSearchParams<{
      id: string;
    }>();

  const profile =
    getProfessionalById(
      params.id,
    );

  const [activeTab, setActiveTab] =
    useState<ProfileTab>("work");

  const commentsRef =
    useRef<BottomSheetModal>(null);

  const [selectedPostId, setSelectedPostId] =
    useState<string | null>(null);

  const posts = useMemo(
    () =>
      profile
        ? getPostsByAuthorId(
            profile.id,
          )
        : [],
    [profile],
  );

  const services = useMemo(
    () =>
      profile
        ? getServicesByAuthorId(
            profile.id,
          )
        : [],
    [profile],
  );

  const selectedPost =
    selectedPostId
      ? posts.find(
          (post) =>
            post.id ===
            selectedPostId,
        )
      : undefined;

  if (!profile) {
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
          title="Perfil não encontrado"
          description="Esse profissional não está disponível no momento."
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

  const firstService =
    services[0];

  const openComments = (
    postId: string,
  ) => {
    setSelectedPostId(
      postId,
    );

    requestAnimationFrame(
      () => {
        commentsRef.current?.present();
      },
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
            styles.coverWrap
          }
        >
          {profile.cover ? (
            <Image
              source={{
                uri: profile.cover,
              }}
              style={
                styles.cover
              }
              contentFit="cover"
              transition={220}
              accessibilityLabel={`Capa de ${profile.name}`}
            />
          ) : (
            <View
              style={
                styles.coverFallback
              }
            />
          )}

          <View
            style={
              styles.coverOverlay
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
                kind="professionals"
                id={profile.id}
              />

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Compartilhar perfil"
                onPress={() => {
                  // Share real entra depois.
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
            styles.profileMain
          }
        >
          <View
            style={
              styles.avatarRow
            }
          >
            <Avatar
              name={
                profile.name
              }
              uri={
                profile.avatar
              }
              size={88}
              ring="plum"
            />

            <FollowButton
              id={
                profile.id
              }
              authorName={
                profile.name
              }
            />
          </View>

          <Text
            style={
              styles.name
            }
          >
            {profile.name}
          </Text>

          <Text
            style={
              styles.specialty
            }
          >
            {profile.specialty}
          </Text>

          <View
            style={
              styles.metaRow
            }
          >
            <Rating
              value={
                profile.rating
              }
            />

            <View
              style={
                styles.metaSeparator
              }
            />

            <Text
              style={
                styles.metaText
              }
            >
              {
                profile.reviewsCount
              }{" "}
              avaliações
            </Text>

            <View
              style={
                styles.metaSeparator
              }
            />

            <View
              style={
                styles.locationRow
              }
            >
              <Icon
                name="map-pin"
                size={12}
                color={
                  colors.muted
                }
              />

              <Text
                style={
                  styles.metaText
                }
              >
                {
                  profile.location
                }
              </Text>
            </View>
          </View>

          {profile.bio ? (
            <Text
              style={
                styles.bio
              }
            >
              {profile.bio}
            </Text>
          ) : null}

          <View
            style={
              styles.categories
            }
          >
            {profile.categories.map(
              (
                category,
              ) => (
                <View
                  key={
                    category
                  }
                  style={
                    styles.categoryBadge
                  }
                >
                  <Text
                    style={
                      styles.categoryText
                    }
                  >
                    {
                      category
                    }
                  </Text>
                </View>
              ),
            )}
          </View>
        </View>

        <View
          style={
            styles.stats
          }
        >
          <View
            style={
              styles.stat
            }
          >
            <Text
              style={
                styles.statValue
              }
            >
              {posts.length}
            </Text>

            <Text
              style={
                styles.statLabel
              }
            >
              Trabalhos
            </Text>
          </View>

          <View
            style={
              styles.statDivider
            }
          />

          <View
            style={
              styles.stat
            }
          >
            <Text
              style={
                styles.statValue
              }
            >
              {services.length}
            </Text>

            <Text
              style={
                styles.statLabel
              }
            >
              Serviços
            </Text>
          </View>

          <View
            style={
              styles.statDivider
            }
          />

          <View
            style={
              styles.stat
            }
          >
            <Text
              style={
                styles.statValue
              }
            >
              {profile.rating.toFixed(
                1,
              )}
            </Text>

            <Text
              style={
                styles.statLabel
              }
            >
              Reputação
            </Text>
          </View>
        </View>

        <View
          style={
            styles.tabs
          }
        >
          {tabs.map(
            (tab) => {
              const active =
                activeTab ===
                tab.id;

              return (
                <Pressable
                  key={
                    tab.id
                  }
                  accessibilityRole="button"
                  accessibilityState={{
                    selected:
                      active,
                  }}
                  onPress={() =>
                    setActiveTab(
                      tab.id,
                    )
                  }
                  style={
                    styles.tab
                  }
                >
                  <Text
                    style={[
                      styles.tabText,

                      active &&
                        styles.tabTextActive,
                    ]}
                  >
                    {
                      tab.label
                    }
                  </Text>

                  {active ? (
                    <View
                      style={
                        styles.tabIndicator
                      }
                    />
                  ) : null}
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
          "work" ? (
            posts.length >
            0 ? (
              <View
                style={
                  styles.posts
                }
              >
                {posts.map(
                  (post) => {
                    const service =
                      getPostService(
                        post,
                      );

                    return (
                      <PostCard
                        key={
                          post.id
                        }
                        id={
                          post.id
                        }
                        author={{
                          id:
                            profile.id,
                          name:
                            profile.name,
                          avatar:
                            profile.avatar,
                          kind:
                            profile.kind,
                          specialty:
                            profile.specialty,
                        }}
                        image={
                          post.image
                        }
                        caption={
                          post.caption
                        }
                        rating={
                          post.rating
                        }
                        commentsCount={
                          post.commentsCount
                        }
                        showFollow={
                          false
                        }
                        service={
                          service
                            ? {
                                id:
                                  service.id,
                                name:
                                  service.name,
                                price:
                                  service.price,
                                availabilityLabel:
                                  service.availabilityLabel,
                              }
                            : undefined
                        }
                        onCommentsPress={() =>
                          openComments(
                            post.id,
                          )
                        }
                      />
                    );
                  },
                )}
              </View>
            ) : (
              <EmptyState
                title="Nenhum trabalho publicado"
                description="Os trabalhos desse profissional aparecerão aqui."
                compact
              />
            )
          ) : activeTab ===
            "services" ? (
            services.length >
            0 ? (
              <View
                style={
                  styles.serviceList
                }
              >
                {services.map(
                  (
                    service,
                  ) => (
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
                        profile.name
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
                  ),
                )}
              </View>
            ) : (
              <EmptyState
                title="Nenhum serviço cadastrado"
                description="Os serviços disponíveis aparecerão aqui."
                compact
              />
            )
          ) : (
            <View
              style={
                styles.reviewsSection
              }
            >
              <View
                style={
                  styles.reviewSummary
                }
              >
                <Text
                  style={
                    styles.reviewScore
                  }
                >
                  {profile.rating.toFixed(
                    1,
                  )}
                </Text>

                <Rating
                  value={
                    profile.rating
                  }
                />

                <Text
                  style={
                    styles.reviewCount
                  }
                >
                  Baseado em{" "}
                  {
                    profile.reviewsCount
                  }{" "}
                  avaliações
                </Text>
              </View>

              <View
                style={
                  styles.reviewCard
                }
              >
                <View
                  style={
                    styles.reviewHeader
                  }
                >
                  <Avatar
                    name="Marina Silva"
                    size={36}
                  />

                  <View
                    style={
                      styles.reviewAuthorArea
                    }
                  >
                    <Text
                      style={
                        styles.reviewAuthor
                      }
                    >
                      Marina Silva
                    </Text>

                    <Rating
                      value={5}
                      small
                    />
                  </View>

                  <Text
                    style={
                      styles.reviewDate
                    }
                  >
                    2d
                  </Text>
                </View>

                <Text
                  style={
                    styles.reviewText
                  }
                >
                  Atendimento excelente, cuidado em cada detalhe e resultado impecável.
                </Text>
              </View>

              <View
                style={
                  styles.reviewCard
                }
              >
                <View
                  style={
                    styles.reviewHeader
                  }
                >
                  <Avatar
                    name="Ana Costa"
                    size={36}
                  />

                  <View
                    style={
                      styles.reviewAuthorArea
                    }
                  >
                    <Text
                      style={
                        styles.reviewAuthor
                      }
                    >
                      Ana Costa
                    </Text>

                    <Rating
                      value={5}
                      small
                    />
                  </View>

                  <Text
                    style={
                      styles.reviewDate
                    }
                  >
                    5d
                  </Text>
                </View>

                <Text
                  style={
                    styles.reviewText
                  }
                >
                  Experiência muito boa. Ambiente agradável e atendimento super profissional.
                </Text>
              </View>
            </View>
          )}
        </View>

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>

      {firstService ? (
        <View
          style={
            styles.stickyBar
          }
        >
          <View
            style={
              styles.stickyInfo
            }
          >
            <Text
              style={
                styles.stickyLabel
              }
            >
              A partir de
            </Text>

            <Text
              style={
                styles.stickyPrice
              }
            >
              {new Intl.NumberFormat(
                "pt-BR",
                {
                  style:
                    "currency",
                  currency:
                    "BRL",
                },
              ).format(
                firstService.price,
              )}
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Agendar com ${profile.name}`}
            onPress={() =>
              router.push(
                `/booking/${firstService.id}`,
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
                styles.bookText
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
      ) : null}

      <CommentsSheet
        ref={commentsRef}
        postId={
          selectedPost?.id ??
          ""
        }
        postAuthor={{
          id: profile.id,
          name: profile.name,
          kind: profile.kind,
        }}
        onRequireLogin={() => {
          commentsRef.current?.dismiss();

          router.push(
            "/login",
          );
        }}
      />
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
      paddingBottom: 100,
    },

    notFoundHeader: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
    },

    coverWrap: {
      width: "100%",
      height: 300,
      position: "relative",
      backgroundColor:
        colors.surfaceTertiary,
    },

    cover: {
      width: "100%",
      height: "100%",
    },

    coverFallback: {
      flex: 1,
      backgroundColor:
        colors.deepViolet,
    },

    coverOverlay: {
      position: "absolute",
      inset: 0,

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

    profileMain: {
      paddingHorizontal:
        spacing.lg,
    },

    avatarRow: {
      marginTop: -44,

      minHeight: 90,

      flexDirection:
        "row",

      alignItems:
        "flex-end",

      justifyContent:
        "space-between",
    },

    name: {
      marginTop:
        spacing.lg,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 30,
      lineHeight: 36,

      letterSpacing: -0.4,
    },

    specialty: {
      marginTop:
        spacing.xs,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 13,
      lineHeight: 17,
    },

    metaRow: {
      marginTop:
        spacing.md,

      flexDirection:
        "row",

      alignItems:
        "center",

      flexWrap: "wrap",

      gap: spacing.sm,
    },

    metaSeparator: {
      width: 3,
      height: 3,

      borderRadius: 2,

      backgroundColor:
        colors.muted,
    },

    locationRow: {
      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.xs,
    },

    metaText: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 14,
    },

    bio: {
      maxWidth: 360,

      marginTop:
        spacing.lg,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 13,
      lineHeight: 20,
    },

    categories: {
      marginTop:
        spacing.lg,

      flexDirection:
        "row",

      flexWrap: "wrap",

      gap: spacing.sm,
    },

    categoryBadge: {
      paddingHorizontal:
        spacing.md,

      paddingVertical: 6,

      borderRadius:
        radius.pill,

      backgroundColor:
        colors.glassSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    categoryText: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 13,
    },

    stats: {
      marginTop:
        spacing.xl,

      marginHorizontal:
        spacing.lg,

      minHeight: 76,

      flexDirection:
        "row",

      alignItems:
        "center",

      borderRadius:
        radius.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    stat: {
      flex: 1,

      alignItems:
        "center",

      justifyContent:
        "center",
    },

    statValue: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 20,
      lineHeight: 25,
    },

    statLabel: {
      marginTop: 2,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 9,
      lineHeight: 12,
    },

    statDivider: {
      width: 1,
      height: 34,

      backgroundColor:
        colors.divider,
    },

    tabs: {
      marginTop:
        spacing.xxl,

      paddingHorizontal:
        spacing.lg,

      minHeight: 50,

      flexDirection:
        "row",

      borderBottomWidth: 1,

      borderBottomColor:
        colors.divider,
    },

    tab: {
      flex: 1,

      minHeight: 50,

      alignItems:
        "center",

      justifyContent:
        "center",

      position: "relative",
    },

    tabText: {
      color:
        colors.muted,

      fontFamily:
        fonts.sansMedium,

      fontSize: 12,
      lineHeight: 16,
    },

    tabTextActive: {
      color:
        colors.onSurface,
    },

    tabIndicator: {
      position: "absolute",

      left: 18,
      right: 18,
      bottom: -1,

      height: 2,

      borderRadius: 1,

      backgroundColor:
        colors.plum,
    },

    tabContent: {
      marginTop:
        spacing.lg,
    },

    posts: {
      gap:
        spacing.xxl,
    },

    serviceList: {
      paddingHorizontal:
        spacing.lg,

      gap: spacing.sm,
    },

    reviewsSection: {
      paddingHorizontal:
        spacing.lg,

      gap: spacing.md,
    },

    reviewSummary: {
      alignItems:
        "center",

      paddingVertical:
        spacing.xl,
    },

    reviewScore: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 42,
      lineHeight: 48,
    },

    reviewCount: {
      marginTop:
        spacing.sm,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
    },

    reviewCard: {
      padding:
        spacing.md,

      borderRadius:
        radius.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    reviewHeader: {
      flexDirection:
        "row",

      alignItems:
        "center",
    },

    reviewAuthorArea: {
      flex: 1,

      marginLeft:
        spacing.sm,
    },

    reviewAuthor: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 12,
      lineHeight: 16,

      marginBottom: 2,
    },

    reviewDate: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 10,
    },

    reviewText: {
      marginTop:
        spacing.md,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 12,
      lineHeight: 18,
    },

    stickyBar: {
      position: "absolute",

      left: 0,
      right: 0,
      bottom: 0,

      minHeight: 86,

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

    stickyInfo: {
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

      fontSize: 17,
      lineHeight: 21,
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

    bookText: {
      color:
        colors.onBrandPrimary,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    bottomSpace: {
      height: 44,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);