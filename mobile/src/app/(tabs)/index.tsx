import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  Share,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { BottomSheetModal } from "@gorhom/bottom-sheet";

import {
  getFeed,
  type FeedMode,
  type WorkPost,
} from "@/api/feed";

import {
  getNotifications,
} from "@/api/notifications";

import { CommentsSheet } from "@/components/CommentsSheet";
import { EditorialBlock } from "@/components/EditorialBlock";
import { EmptyState } from "@/components/EmptyState";
import { IDDUNNowCard } from "@/components/IDDUNNowCard";
import { Icon } from "@/components/Icon";
import { PostCard } from "@/components/PostCard";
import { ProfessionalCard } from "@/components/ProfessionalCard";
import { SectionHeader } from "@/components/SectionHeader";
import { StoryAvatar } from "@/components/StoryAvatar";

import {
  getIDDUNNowData,
  getStoryProfile,
  iddunNowItems,
  professionals,
  stories,
} from "@/mocks/data";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function HomeScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const commentsRef =
    useRef<BottomSheetModal>(null);

  const [selectedPostId, setSelectedPostId] =
    useState<string | null>(null);

  const [refreshing, setRefreshing] =
    useState(false);

  const [feedMode, setFeedMode] =
    useState<FeedMode>("for-you");

  const [
    feedPosts,
    setFeedPosts,
  ] =
    useState<WorkPost[]>([]);

  const [
    feedLoading,
    setFeedLoading,
  ] =
    useState(true);

  const [
    feedError,
    setFeedError,
  ] =
    useState<string | null>(
      null,
    );

  const [
    nextCursor,
    setNextCursor,
  ] =
    useState<string | null>(
      null,
    );

  const [
    loadingMore,
    setLoadingMore,
  ] =
    useState(false);

  const [
    notificationsCount,
    setNotificationsCount,
  ] = useState(0);

  useEffect(() => {
    let mounted = true;

    const loadNotificationCount =
      async () => {
        const user =
          store.getUser();

        if (!user) {
          if (mounted) {
            setNotificationsCount(
              0,
            );
          }
          return;
        }

        try {
          const response =
            await getNotifications({
              limit: 1,
            });

          if (mounted) {
            setNotificationsCount(
              response.unreadCount,
            );
          }
        } catch {
          if (mounted) {
            setNotificationsCount(
              0,
            );
          }
        }
      };

    void loadNotificationCount();

    return () => {
      mounted = false;
    };
  }, []);

  const storyData = useMemo(() => {
    return stories
      .map((story) => {
        const profile =
          getStoryProfile(story);

        if (!profile) {
          return null;
        }

        return {
          story,
          profile,
        };
      })
      .filter(Boolean) as {
      story: (typeof stories)[number];
      profile: (typeof professionals)[number];
    }[];
  }, []);

  useEffect(
    () => {
      let mounted =
        true;

      getFeed({
        mode:
          feedMode,
      })
        .then(
          (response) => {
            if (!mounted) {
              return;
            }

            setFeedPosts(
              response.items,
            );
            setNextCursor(
              response.nextCursor ??
              null,
            );
            setFeedError(
              null,
            );
          },
        )
        .catch(
          (error) => {
            if (!mounted) {
              return;
            }

            setFeedPosts(
              [],
            );
            setFeedError(
              error instanceof Error
                ? error.message
                : "Não foi possível carregar o feed.",
            );
          },
        )
        .finally(
          () => {
            if (mounted) {
              setFeedLoading(
                false,
              );
            }
          },
        );

      return () => {
        mounted = false;
      };
    },
    [feedMode],
  );

  const selectedPost =
    selectedPostId
      ? feedPosts.find(
          (post) =>
            post.id ===
            selectedPostId,
        )
      : undefined;

  const selectedPostAuthor =
    selectedPost?.author;

  const handleOpenComments = (
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

  const handleRefresh =
    async () => {
      setRefreshing(true);

      try {
        const response =
          await getFeed({
            mode:
              feedMode,
          });

        setFeedPosts(
          response.items,
        );
        setNextCursor(
          response.nextCursor ??
          null,
        );
        setFeedError(
          null,
        );
      } catch (error) {
        setFeedError(
          error instanceof Error
            ? error.message
            : "Não foi possível atualizar o feed.",
        );
      } finally {
        setRefreshing(false);
      }
    };

  const handleLoadMore =
    async () => {
      if (
        !nextCursor ||
        loadingMore
      ) {
        return;
      }

      try {
        setLoadingMore(
          true,
        );

        const response =
          await getFeed({
            mode:
              feedMode,
            cursor:
              nextCursor,
          });

        setFeedPosts(
          (current) => {
            const ids =
              new Set(
                current.map(
                  (item) =>
                    item.id,
                ),
              );

            return [
              ...current,
              ...response.items.filter(
                (item) =>
                  !ids.has(
                    item.id,
                  ),
              ),
            ];
          },
        );

        setNextCursor(
          response.nextCursor ??
          null,
        );
      } catch (error) {
        setFeedError(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar mais publicações.",
        );
      } finally {
        setLoadingMore(
          false,
        );
      }
    };

  const renderFeedPost = (
    post: WorkPost,
  ) => {
    const author =
      post.author;

    const service =
      post.service ??
      undefined;

    const handleShare =
      async () => {
        await Share.share({
          message:
            (
              post.caption
                ? post.caption
                  + "\n\n"
                : ""
            )
            + "Veja este trabalho no IDDUN: "
            + post.deepLink,
        });
      };

    return (
      <PostCard
        key={post.id}
        id={post.id}
        author={{
          id: author.id,
          routeId:
            author.routeId,
          name: author.name,
          avatar:
            author.avatar,
          kind:
            author.kind,
          specialty:
            author.specialty ??
            undefined,
        }}
        image={post.image}
        caption={
          post.caption
        }
        rating={
          author.rating ??
          undefined
        }
        commentsCount={
          post.commentsCount
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
                  service.availabilityLabel ??
                  undefined,
              }
            : undefined
        }
        onCommentsPress={() =>
          handleOpenComments(
            post.id,
          )
        }
        onSharePress={() =>
          void handleShare()
        }
      />
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
        refreshControl={
          <RefreshControl
            refreshing={
              refreshing
            }
            onRefresh={
              handleRefresh
            }
            tintColor={
              colors.plum
            }
          />
        }
      >
        <View
          style={
            styles.header
          }
        >
          <View style={styles.brandRow}>
            <Image
                source={require("../../../assets/branding/iddun-logo-white.png")}
                style={styles.logo}
                contentFit="contain"
                accessibilityLabel="IDDUN"
            />
        </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={
              notificationsCount >
              0
                ? `${notificationsCount} notificações não lidas`
                : "Notificações"
            }
            onPress={() =>
              router.push(
                "/notifications",
              )
            }
            style={({
              pressed,
            }) => [
              styles.notificationButton,
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

            {notificationsCount >
            0 ? (
              <View
                style={
                  styles.notificationBadge
                }
              >
                <Text
                  style={
                    styles.notificationBadgeText
                  }
                >
                  {notificationsCount >
                  9
                    ? "9+"
                    : notificationsCount}
                </Text>
              </View>
            ) : null}
          </Pressable>
        </View>

        <View
          style={
            styles.feedSwitcher
          }
        >
          <Pressable
            accessibilityRole="button"
            accessibilityState={{
              selected:
                feedMode ===
                "for-you",
            }}
            onPress={() =>
              setFeedMode(
                "for-you",
              )
            }
            style={({ pressed }) => [
              styles.feedTab,
              pressed &&
                styles.pressed,
            ]}
          >
            <Text
              style={[
                styles.feedTabText,

                feedMode ===
                  "for-you" &&
                  styles.feedTabTextActive,
              ]}
            >
              Para você
            </Text>

            {feedMode ===
            "for-you" ? (
              <View
                style={
                  styles.feedTabIndicator
                }
              />
            ) : null}
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityState={{
              selected:
                feedMode ===
                "following",
            }}
            onPress={() =>
              setFeedMode(
                "following",
              )
            }
            style={({ pressed }) => [
              styles.feedTab,
              pressed &&
                styles.pressed,
            ]}
          >
            <Text
              style={[
                styles.feedTabText,

                feedMode ===
                  "following" &&
                  styles.feedTabTextActive,
              ]}
            >
              Seguindo
            </Text>

            {feedMode ===
            "following" ? (
              <View
                style={
                  styles.feedTabIndicator
                }
              />
            ) : null}
          </Pressable>
        </View>

        <View
          style={
            styles.storiesSection
          }
        >
          <FlatList
            horizontal
            data={storyData}
            keyExtractor={({
              story,
            }) => story.id}
            showsHorizontalScrollIndicator={
              false
            }
            contentContainerStyle={
              styles.storiesContent
            }
            renderItem={({
              item,
            }) => (
              <StoryAvatar
                id={
                  item.profile.id
                }
                name={
                  item.profile.name
                }
                uri={
                  item.profile.avatar
                }
                seen={
                  item.story.seen
                }
                routeType={
                  item.profile.kind
                }
              />
            )}
          />
        </View>

        {feedMode ===
          "for-you" && (
          <>
            <View
              style={
                styles.section
              }
            >
              <SectionHeader
                title="IDDUN Now"
                subtitle="Horários que acabaram de abrir"
                actionLabel="Ver todos"
                showSpark
                onActionPress={() =>
                  router.push(
                    "/iddun-now",
                  )
                }
              />

              <FlatList
                horizontal
                data={
                  iddunNowItems
                }
                keyExtractor={(
                  item,
                ) => item.id}
                showsHorizontalScrollIndicator={
                  false
                }
                contentContainerStyle={
                  styles.horizontalCards
                }
                renderItem={({
                  item,
                }) => {
                  const data =
                    getIDDUNNowData(
                      item,
                    );

                  if (!data) {
                    return null;
                  }

                  return (
                    <IDDUNNowCard
                      serviceId={
                        data.service
                          .id
                      }
                      professionalId={
                        data
                          .professional
                          .id
                      }
                      professionalName={
                        data
                          .professional
                          .name
                      }
                      professionalAvatar={
                        data
                          .professional
                          .avatar
                      }
                      serviceName={
                        data.service
                          .name
                      }
                      image={
                        data.service
                          .image
                      }
                      price={
                        data.service
                          .price
                      }
                      timeLabel={
                        item.timeLabel
                      }
                      location={
                        data.service
                          .location
                      }
                      routeType={
                        data
                          .professional
                          .kind
                      }
                      urgent={
                        item.urgent
                      }
                    />
                  );
                }}
              />
            </View>

            <View
              style={
                styles.editorialSection
              }
            >
              <EditorialBlock
                eyebrow="EDIÇÃO CURITIBA"
                title="Beleza que vira experiência."
                subtitle="Uma curadoria de profissionais, espaços e técnicas para descobrir sem pressa."
                image="https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=1200&q=90"
                actionLabel="Descobrir"
                onPress={() =>
                  router.push(
                    "/(tabs)/discover",
                  )
                }
              />
            </View>

            <View
              style={
                styles.section
              }
            >
              <SectionHeader
                title="Profissionais para conhecer"
                subtitle="Novos nomes para entrar no seu radar"
                actionLabel="Explorar"
                onActionPress={() =>
                  router.push(
                    "/(tabs)/discover",
                  )
                }
              />

              <View
                style={
                  styles.professionalsList
                }
              >
                {professionals
                  .slice(0, 3)
                  .map(
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
          </>
        )}

        <View
          style={
            styles.feedSection
          }
        >
          {feedLoading ? (
            <View
              style={
                styles.feedLoading
              }
              accessibilityRole="progressbar"
              accessibilityLabel="Carregando publicações"
            >
              <ActivityIndicator
                color={
                  colors.plum
                }
              />
            </View>
          ) : feedPosts.length >
          0 ? (
            <>
              {feedPosts.map(
                renderFeedPost,
              )}

              {nextCursor ? (
                <View
                  style={
                    styles.loadMoreWrap
                  }
                >
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Carregar mais publicações"
                    disabled={
                      loadingMore
                    }
                    onPress={() =>
                      void handleLoadMore()
                    }
                    style={({ pressed }) => [
                      styles.loadMoreButton,
                      pressed &&
                        styles.pressed,
                    ]}
                  >
                    {loadingMore ? (
                      <ActivityIndicator
                        size="small"
                        color={
                          colors.plum
                        }
                      />
                    ) : (
                      <Text
                        style={
                          styles.loadMoreText
                        }
                      >
                        Carregar mais
                      </Text>
                    )}
                  </Pressable>
                </View>
              ) : null}
            </>
          ) : (
            <EmptyState
              title={
                feedError
                  ? "Não foi possível carregar o feed"
                  : "Seu feed está começando"
              }
              description={
                feedError ??
                (
                  feedMode ===
                  "following"
                    ? "Siga profissionais e estabelecimentos para acompanhar os trabalhos deles aqui."
                    : "Ainda não há publicações disponíveis. Os próximos trabalhos publicados aparecem aqui."
                )
              }
              actionLabel="Descobrir perfis"
              onActionPress={() =>
                router.push(
                  "/(tabs)/discover",
                )
              }
            />
          )}
        </View>

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>

      <CommentsSheet
        ref={commentsRef}
        postId={
          selectedPostId ??
          ""
        }
        postAuthor={
          selectedPostAuthor
            ? {
                id:
                  selectedPostAuthor.id,
                name:
                  selectedPostAuthor.name,
                kind:
                  selectedPostAuthor.kind,
              }
            : undefined
        }
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

      brandRow: {
        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.xs,
      },

      logo: {
        width: 112,
        height: 34,
      },

      brand: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 23,
        lineHeight: 28,

        letterSpacing: 2.6,
      },

      brandSpark: {
        color:
          colors.plum,

        fontFamily:
          fonts.display,

        fontSize: 13,
      },

      notificationButton: {
        width:
          touch.minimum,

        height:
          touch.minimum,

        alignItems:
          "center",

        justifyContent:
          "center",

        borderRadius: 999,

        backgroundColor:
          colors.glassSoft,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      notificationBadge: {
        position:
          "absolute",

        top: 4,
        right: 3,

        minWidth: 17,
        height: 17,

        paddingHorizontal: 4,

        borderRadius: 9,

        alignItems:
          "center",

        justifyContent:
          "center",

        backgroundColor:
          colors.plum,

        borderWidth: 2,

        borderColor:
          colors.surface,
      },

      notificationBadgeText: {
        color:
          colors.onBrandPrimary,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 8,
        lineHeight: 10,
      },

      feedSwitcher: {
        marginTop:
          spacing.md,

        paddingHorizontal:
          spacing.lg,

        flexDirection:
          "row",

        gap: spacing.xl,
      },

      feedTab: {
        minHeight:
          touch.minimum,

        justifyContent:
          "center",

        position:
          "relative",
      },

      feedTabText: {
        color:
          colors.muted,

        fontFamily:
          fonts.sansMedium,

        fontSize: 13,
        lineHeight: 17,
      },

      feedTabTextActive: {
        color:
          colors.onSurface,
      },

      feedTabIndicator: {
        position:
          "absolute",

        left: 0,
        right: 0,
        bottom: 0,

        height: 2,

        borderRadius: 1,

        backgroundColor:
          colors.plum,
      },

      storiesSection: {
        marginTop:
          spacing.sm,

        paddingBottom:
          spacing.md,

        borderBottomWidth: 1,

        borderBottomColor:
          colors.divider,
      },

      storiesContent: {
        paddingHorizontal:
          spacing.lg,

        gap: spacing.sm,
      },

      section: {
        marginTop:
          spacing.xxl,

        gap: spacing.lg,

        paddingHorizontal:
          spacing.lg,
      },

      horizontalCards: {
        gap: spacing.md,

        paddingRight:
          spacing.lg,
      },

      editorialSection: {
        marginTop:
          spacing.xxl,

        paddingHorizontal:
          spacing.lg,
      },

      professionalsList: {
        gap: spacing.sm,
      },

      feedSection: {
        marginTop:
          spacing.xxl,

        gap:
          spacing.xxl,
      },

      feedLoading: {
        minHeight: 180,
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      loadMoreWrap: {
        paddingHorizontal:
          spacing.lg,
        alignItems:
          "center",
      },

      loadMoreButton: {
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.xl,
        borderRadius: 999,
        borderWidth: 1,
        borderColor:
          colors.border,
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      loadMoreText: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 12,
        color:
          colors.onSurface,
      },

      bottomSpace: {
        height: 120,
      },

      pressed: {
        opacity: 0.75,
      },
    }),
  );