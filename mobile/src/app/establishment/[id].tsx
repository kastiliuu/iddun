import React, {
  useEffect,
  useMemo,
  useRef,
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
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import { BottomSheetModal } from "@gorhom/bottom-sheet";

import {
  getEstablishment,
  type EstablishmentProfileResponse,
} from "@/api/establishments";

import { Avatar } from "@/components/Avatar";
import { CommentsSheet } from "@/components/CommentsSheet";
import { EmptyState } from "@/components/EmptyState";
import { FavoriteButton } from "@/components/FavoriteButton";
import { FollowButton } from "@/components/FollowButton";
import { Icon } from "@/components/Icon";
import { PostCard } from "@/components/PostCard";
import { ProfessionalCard } from "@/components/ProfessionalCard";
import { Rating } from "@/components/Rating";
import { ServiceCard } from "@/components/ServiceCard";

import {
  getPostService,
  getPostsByAuthorId,
  getProfessionalById,
  getServicesByAuthorId,
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

type EstablishmentTab =
  | "work"
  | "services"
  | "team"
  | "reviews";

const tabs: {
  id: EstablishmentTab;
  label: string;
}[] = [
  {
    id: "work",
    label: "Trabalhos",
  },
  {
    id: "services",
    label: "Serviços",
  },
  {
    id: "team",
    label: "Equipe",
  },
  {
    id: "reviews",
    label: "Avaliações",
  },
];

export default function EstablishmentProfileScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const params =
    useLocalSearchParams<{
      id: string;
    }>();

  const mockEstablishment =
    getProfessionalById(
      params.id,
    );

  const [
    remoteData,
    setRemoteData,
  ] =
    useState<EstablishmentProfileResponse | null>(
      null,
    );

  const [
    remoteLoading,
    setRemoteLoading,
  ] =
    useState(
      !mockEstablishment,
    );

  useEffect(
    () => {
      if (
        mockEstablishment
      ) {
        return;
      }

      let mounted =
        true;

      getEstablishment(
        params.id,
      )
        .then(
          (response) => {
            if (mounted) {
              setRemoteData(
                response,
              );
            }
          },
        )
        .catch(
          () => {
            if (mounted) {
              setRemoteData(
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
      mockEstablishment,
      params.id,
    ],
  );

  const establishment =
    mockEstablishment ??
    remoteData?.establishment;

  const [activeTab, setActiveTab] =
    useState<EstablishmentTab>("work");

  const commentsRef =
    useRef<BottomSheetModal>(null);

  const [selectedPostId, setSelectedPostId] =
    useState<string | null>(null);

  const posts = useMemo(
    () => {
      if (
        mockEstablishment
      ) {
        return getPostsByAuthorId(
          mockEstablishment.id,
        );
      }

      return (
        remoteData?.posts ??
        []
      ).map(
        (post) => ({
          id: post.id,
          authorId:
            post.authorId,
          image:
            post.image,
          caption:
            post.caption,
          rating:
            post.author
              .rating ??
            undefined,
          commentsCount:
            post.commentsCount,
          serviceId:
            post.service?.id ??
            undefined,
          createdAt:
            post.publishedAt ??
            "",
        }),
      );
    },
    [
      mockEstablishment,
      remoteData,
    ],
  );

  const services = useMemo(
    () =>
      mockEstablishment
        ? getServicesByAuthorId(
            mockEstablishment.id,
          )
        : (
            remoteData
              ?.services ??
            []
          ),
    [
      mockEstablishment,
      remoteData,
    ],
  );

  const team = useMemo(
    () =>
      mockEstablishment
        ? professionals
            .filter(
              (profile) =>
                profile.kind ===
                "professional",
            )
            .slice(0, 3)
        : (
            remoteData
              ?.team ??
            []
          ),
    [
      mockEstablishment,
      remoteData,
    ],
  );

  const selectedPost =
    selectedPostId
      ? posts.find(
          (post) =>
            post.id ===
            selectedPostId,
        )
      : undefined;

  if (
    remoteLoading &&
    !establishment
  ) {
    return (
      <View
        style={
          styles.loading
        }
        accessibilityRole="progressbar"
        accessibilityLabel="Carregando estabelecimento"
      >
        <ActivityIndicator
          color={
            colors.plum
          }
        />
      </View>
    );
  }

  if (
    !establishment ||
    establishment.kind !==
      "establishment"
  ) {
    return (
      <View style={styles.container}>
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
          title="Estabelecimento não encontrado"
          description="Esse espaço não está disponível no momento."
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
    <View style={styles.container}>
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
          {establishment.cover ? (
            <Image
              source={{
                uri: establishment.cover,
              }}
              style={
                styles.cover
              }
              contentFit="cover"
              transition={220}
              accessibilityLabel={`Capa de ${establishment.name}`}
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
                targetType="establishment"
                id={
                  establishment.id
                }
              />

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Compartilhar estabelecimento"
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
                establishment.name
              }
              uri={
                establishment.avatar
              }
              size={88}
              ring="plum"
            />

            <FollowButton
              id={
                establishment.id
              }
              targetType="establishment"
              authorName={
                establishment.name
              }
            />
          </View>

          <View
            style={
              styles.typeBadge
            }
          >
            <Icon
              name="home"
              size={12}
              color={
                colors.plum
              }
            />

            <Text
              style={
                styles.typeBadgeText
              }
            >
              ESTABELECIMENTO
            </Text>
          </View>

          <Text
            style={
              styles.name
            }
          >
            {establishment.name}
          </Text>

          <Text
            style={
              styles.specialty
            }
          >
            {
              establishment.specialty
            }
          </Text>

          <View
            style={
              styles.metaRow
            }
          >
            <Rating
              value={
                establishment.rating
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
                establishment.reviewsCount
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
                  establishment.location
                }
              </Text>
            </View>
          </View>

          {establishment.bio ? (
            <Text
              style={
                styles.bio
              }
            >
              {establishment.bio}
            </Text>
          ) : null}

          <View
            style={
              styles.categories
            }
          >
            {establishment.categories.map(
              (category) => (
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
                    {category}
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
              {team.length}
            </Text>

            <Text
              style={
                styles.statLabel
              }
            >
              Profissionais
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
              {establishment.rating.toFixed(
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
            styles.reputationInfo
          }
        >
          <Icon
            name="star"
            size={17}
            color={
              colors.plum
            }
          />

          <Text
            style={
              styles.reputationText
            }
          >
            A reputação do estabelecimento será composta pelas avaliações recebidas pelo espaço e pela reputação dos profissionais vinculados.
          </Text>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={
            false
          }
          contentContainerStyle={
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
        </ScrollView>

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
                      mockEstablishment
                        ? getPostService(
                            post,
                          )
                        : services.find(
                            (item) =>
                              item.id ===
                              post.serviceId,
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
                            establishment.id,
                          routeId:
                            establishment.routeId ??
                            params.id,
                          name:
                            establishment.name,
                          avatar:
                            establishment.avatar,
                          kind:
                            "establishment",
                          specialty:
                            establishment.specialty,
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
                description="Os trabalhos deste estabelecimento aparecerão aqui."
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
                  (service) => (
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
                        establishment.name
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
                description="Os serviços deste espaço aparecerão aqui."
                compact
              />
            )
          ) : activeTab ===
            "team" ? (
            team.length >
            0 ? (
              <View
                style={
                  styles.teamSection
                }
              >
                <Text
                  style={
                    styles.teamIntro
                  }
                >
                  Conheça os profissionais vinculados a este estabelecimento.
                </Text>

                <View
                  style={
                    styles.teamList
                  }
                >
                  {team.map(
                    (professional) => (
                      <ProfessionalCard
                        key={
                          professional.id
                        }
                        id={
                          professional.id
                        }
                        routeId={
                          professional.routeId
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
                        routeType="professional"
                      />
                    ),
                  )}
                </View>
              </View>
            ) : (
              <EmptyState
                title="Nenhum profissional vinculado"
                description="A equipe deste estabelecimento aparecerá aqui."
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
                  {establishment.rating.toFixed(
                    1,
                  )}
                </Text>

                <Rating
                  value={
                    establishment.rating
                  }
                />

                <Text
                  style={
                    styles.reviewCount
                  }
                >
                  Baseado em{" "}
                  {
                    establishment.reviewsCount
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
                    name="Juliana Ramos"
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
                      Juliana Ramos
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
                    3d
                  </Text>
                </View>

                <Text
                  style={
                    styles.reviewText
                  }
                >
                  Espaço lindo, atendimento organizado e ótima experiência do início ao fim.
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
                    name="Fernanda Luz"
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
                      Fernanda Luz
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
                    1 sem
                  </Text>
                </View>

                <Text
                  style={
                    styles.reviewText
                  }
                >
                  Gostei muito do ambiente e da equipe. Voltaria com certeza.
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
              Serviços a partir de
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
            accessibilityLabel={`Ver serviços de ${establishment.name}`}
            onPress={() =>
              setActiveTab(
                "services",
              )
            }
            style={({ pressed }) => [
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
              Ver serviços
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
          id:
            establishment.id,
          name:
            establishment.name,
          kind:
            "establishment",
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

      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "space-between",
    },

    topRightActions: {
      flexDirection: "row",

      alignItems: "center",

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

      flexDirection: "row",

      alignItems:
        "flex-end",

      justifyContent:
        "space-between",
    },

    typeBadge: {
      alignSelf:
        "flex-start",

      marginTop:
        spacing.lg,

      paddingHorizontal:
        spacing.sm,

      paddingVertical: 5,

      borderRadius:
        radius.pill,

      flexDirection: "row",

      alignItems: "center",

      gap: spacing.xs,

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    typeBadgeText: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 9,
      lineHeight: 12,

      letterSpacing: 0.7,
    },

    name: {
      marginTop:
        spacing.sm,

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

      flexWrap:
        "wrap",

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

      flexWrap:
        "wrap",

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

    reputationInfo: {
      marginTop:
        spacing.md,

      marginHorizontal:
        spacing.lg,

      padding:
        spacing.md,

      borderRadius:
        radius.md,

      flexDirection:
        "row",

      alignItems:
        "flex-start",

      gap: spacing.sm,

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    reputationText: {
      flex: 1,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 16,
    },

    tabs: {
      marginTop:
        spacing.xxl,

      paddingHorizontal:
        spacing.lg,

      minHeight: 50,

      borderBottomWidth: 1,

      borderBottomColor:
        colors.divider,

      gap: spacing.xl,
    },

    tab: {
      minWidth: 82,

      minHeight: 50,

      alignItems:
        "center",

      justifyContent:
        "center",

      position:
        "relative",
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

      left: 10,
      right: 10,
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

    teamSection: {
      paddingHorizontal:
        spacing.lg,
    },

    teamIntro: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 17,

      marginBottom:
        spacing.lg,
    },

    teamList: {
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