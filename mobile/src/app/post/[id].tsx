import React, {
  useMemo,
  useRef,
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
import { Rating } from "@/components/Rating";

import {
  getPostAuthor,
  getPostById,
  getPostService,
} from "@/mocks/data";

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

export default function PostDetailScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const params =
    useLocalSearchParams<{
      id: string;
    }>();

  const commentsRef =
    useRef<BottomSheetModal>(null);

  const post =
    getPostById(params.id);

  const author = useMemo(
    () =>
      post
        ? getPostAuthor(post)
        : undefined,
    [post],
  );

  const service = useMemo(
    () =>
      post
        ? getPostService(post)
        : undefined,
    [post],
  );

  if (!post || !author) {
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
              if (router.canGoBack()) {
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
          title="Publicação não encontrada"
          description="Essa publicação não está disponível no momento."
          actionLabel="Voltar ao início"
          onActionPress={() =>
            router.replace(
              "/(tabs)",
            )
          }
        />
      </View>
    );
  }

  const openAuthor = () => {
    router.push(
      author.kind ===
        "establishment"
        ? `/establishment/${author.id}`
        : `/professional/${author.id}`,
    );
  };

  const openComments = () => {
    commentsRef.current?.present();
  };

  const openService = () => {
    if (!service) {
      return;
    }

    router.push(
      `/service/${service.id}`,
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
            styles.header
          }
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => {
              if (router.canGoBack()) {
                router.back();
              } else {
                router.replace(
                  "/(tabs)",
                );
              }
            }}
            style={({ pressed }) => [
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
            Publicação
          </Text>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Mais opções"
            onPress={() => {
              // Menu real entra depois.
            }}
            style={({ pressed }) => [
              styles.headerButton,
              pressed &&
                styles.pressed,
            ]}
          >
            <Icon
              name="more-horizontal"
              size={20}
              color={
                colors.onSurface
              }
            />
          </Pressable>
        </View>

        <View
          style={
            styles.authorHeader
          }
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Abrir perfil de ${author.name}`}
            onPress={
              openAuthor
            }
            style={({ pressed }) => [
              styles.authorPressable,
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
              size={46}
            />

            <View
              style={
                styles.authorText
              }
            >
              <Text
                style={
                  styles.authorName
                }
                numberOfLines={1}
              >
                {author.name}
              </Text>

              <Text
                style={
                  styles.authorSubtitle
                }
                numberOfLines={1}
              >
                {author.kind ===
                "establishment"
                  ? "Estabelecimento"
                  : author.specialty}
              </Text>
            </View>
          </Pressable>

          <FollowButton
            id={
              author.id
            }
            targetType={
              author.kind
            }
            authorName={
              author.name
            }
          />
        </View>

        <View
          style={
            styles.mediaWrap
          }
        >
          <Image
            source={{
              uri: post.image,
            }}
            style={
              styles.image
            }
            contentFit="cover"
            transition={220}
            accessibilityLabel={`Publicação de ${author.name}`}
          />
        </View>

        <View
          style={
            styles.actions
          }
        >
          <View
            style={
              styles.leftActions
            }
          >
            <FavoriteButton
              kind="posts"
              id={post.id}
            />

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`${post.commentsCount} comentários`}
              hitSlop={6}
              onPress={
                openComments
              }
              style={({ pressed }) => [
                styles.iconButton,
                pressed &&
                  styles.pressed,
              ]}
            >
              <Icon
                name="message-circle"
                size={21}
                color={
                  colors.onSurface
                }
              />
            </Pressable>

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Compartilhar publicação"
              hitSlop={6}
              onPress={() => {
                // Share real entra depois.
              }}
              style={({ pressed }) => [
                styles.iconButton,
                pressed &&
                  styles.pressed,
              ]}
            >
              <Icon
                name="send"
                size={20}
                color={
                  colors.onSurface
                }
              />
            </Pressable>
          </View>

          {typeof post.rating ===
          "number" ? (
            <Rating
              value={
                post.rating
              }
            />
          ) : null}
        </View>

        <View
          style={
            styles.postContent
          }
        >
          <Text
            style={
              styles.caption
            }
          >
            <Text
              style={
                styles.captionAuthor
              }
            >
              {author.name}{" "}
            </Text>

            {post.caption}
          </Text>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Ver ${post.commentsCount} comentários`}
            onPress={
              openComments
            }
            style={({ pressed }) => [
              styles.commentsButton,
              pressed &&
                styles.pressed,
            ]}
          >
            <Text
              style={
                styles.commentsText
              }
            >
              {post.commentsCount === 1
                ? "Ver 1 comentário"
                : `Ver ${post.commentsCount} comentários`}
            </Text>
          </Pressable>
        </View>

        {service ? (
          <View
            style={
              styles.serviceSection
            }
          >
            <Text
              style={
                styles.sectionEyebrow
              }
            >
              SERVIÇO DESTA PUBLICAÇÃO
            </Text>

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Abrir serviço ${service.name}`}
              onPress={
                openService
              }
              style={({ pressed }) => [
                styles.serviceCard,
                pressed &&
                  styles.pressed,
              ]}
            >
              <Image
                source={{
                  uri: service.image,
                }}
                style={
                  styles.serviceImage
                }
                contentFit="cover"
                transition={180}
                accessibilityLabel={`Serviço ${service.name}`}
              />

              <View
                style={
                  styles.serviceContent
                }
              >
                <Text
                  style={
                    styles.serviceCategory
                  }
                >
                  {service.category.toUpperCase()}
                </Text>

                <Text
                  style={
                    styles.serviceName
                  }
                  numberOfLines={1}
                >
                  {service.name}
                </Text>

                <View
                  style={
                    styles.serviceMeta
                  }
                >
                  <Text
                    style={
                      styles.servicePrice
                    }
                  >
                    {formatCurrency(
                      service.price,
                    )}
                  </Text>

                  {service.availabilityLabel ? (
                    <>
                      <View
                        style={
                          styles.serviceSeparator
                        }
                      />

                      <Text
                        style={
                          styles.serviceAvailability
                        }
                        numberOfLines={1}
                      >
                        {
                          service.availabilityLabel
                        }
                      </Text>
                    </>
                  ) : null}
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
          </View>
        ) : null}

        <View
          style={
            styles.authorSection
          }
        >
          <Text
            style={
              styles.sectionEyebrow
            }
          >
            SOBRE O AUTOR
          </Text>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Abrir perfil de ${author.name}`}
            onPress={
              openAuthor
            }
            style={({ pressed }) => [
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
              size={60}
            />

            <View
              style={
                styles.authorCardContent
              }
            >
              <Text
                style={
                  styles.authorCardName
                }
                numberOfLines={1}
              >
                {author.name}
              </Text>

              <Text
                style={
                  styles.authorCardSpecialty
                }
                numberOfLines={1}
              >
                {
                  author.specialty
                }
              </Text>

              <View
                style={
                  styles.authorCardMeta
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
                    styles.authorCardReviews
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
        </View>

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>

      {service ? (
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
              {service.name}
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
            accessibilityLabel={`Agendar ${service.name}`}
            onPress={() =>
              router.push(
                `/booking/${service.id}`,
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
        postId={post.id}
        postAuthor={{
          id: author.id,
          name: author.name,
          kind: author.kind,
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
      paddingTop: 54,
      paddingBottom: 104,
    },

    notFoundHeader: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
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
      lineHeight: 17,
    },

    authorHeader: {
      minHeight: 72,

      paddingHorizontal:
        spacing.lg,

      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "space-between",

      gap: spacing.md,
    },

    authorPressable: {
      flex: 1,
      minWidth: 0,

      flexDirection:
        "row",

      alignItems:
        "center",
    },

    authorText: {
      flex: 1,
      minWidth: 0,

      marginLeft:
        spacing.sm,
    },

    authorName: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    authorSubtitle: {
      marginTop: 2,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 13,
    },

    mediaWrap: {
      width: "100%",

      aspectRatio: 4 / 5,

      backgroundColor:
        colors.surfaceTertiary,
    },

    image: {
      width: "100%",
      height: "100%",
    },

    actions: {
      minHeight: 54,

      paddingHorizontal:
        spacing.sm,

      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "space-between",
    },

    leftActions: {
      flexDirection:
        "row",

      alignItems:
        "center",
    },

    iconButton: {
      width:
        touch.minimum,

      height:
        touch.minimum,

      alignItems:
        "center",

      justifyContent:
        "center",
    },

    postContent: {
      paddingHorizontal:
        spacing.lg,
    },

    caption: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 13,
      lineHeight: 20,
    },

    captionAuthor: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,
    },

    commentsButton: {
      alignSelf:
        "flex-start",

      minHeight: 38,

      justifyContent:
        "center",

      marginTop:
        spacing.xs,
    },

    commentsText: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 15,
    },

    serviceSection: {
      marginTop:
        spacing.xxxl,

      paddingHorizontal:
        spacing.lg,
    },

    sectionEyebrow: {
      marginBottom:
        spacing.sm,

      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 9,
      lineHeight: 12,

      letterSpacing: 1.2,
    },

    serviceCard: {
      minHeight: 92,

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

    serviceImage: {
      width: 64,
      height: 64,

      borderRadius:
        radius.md,

      backgroundColor:
        colors.surfaceTertiary,
    },

    serviceContent: {
      flex: 1,
      minWidth: 0,
    },

    serviceCategory: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 8,
      lineHeight: 11,

      letterSpacing: 0.7,
    },

    serviceName: {
      marginTop: 2,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    serviceMeta: {
      marginTop:
        spacing.xs,

      minWidth: 0,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,
    },

    servicePrice: {
      flexShrink: 0,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 13,
    },

    serviceSeparator: {
      width: 3,
      height: 3,

      borderRadius: 2,

      backgroundColor:
        colors.muted,
    },

    serviceAvailability: {
      flex: 1,

      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 10,
      lineHeight: 13,
    },

    authorSection: {
      marginTop:
        spacing.xxxl,

      paddingHorizontal:
        spacing.lg,
    },

    authorCard: {
      minHeight: 92,

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

    authorCardContent: {
      flex: 1,
      minWidth: 0,
    },

    authorCardName: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 14,
      lineHeight: 18,
    },

    authorCardSpecialty: {
      marginTop: 2,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 14,
    },

    authorCardMeta: {
      marginTop:
        spacing.xs,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,
    },

    authorCardReviews: {
      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 13,
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

    stickyInfo: {
      flex: 1,
      minWidth: 0,
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
      height: 48,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);