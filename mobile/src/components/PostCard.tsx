import React, {
  useState,
} from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import { Avatar } from "@/components/Avatar";
import { FavoriteButton } from "@/components/FavoriteButton";
import { FollowButton } from "@/components/FollowButton";
import { Icon } from "@/components/Icon";
import { Rating } from "@/components/Rating";
import {
  ReportModal,
  type ReportTarget,
} from "@/components/ReportModal";
import { useToast } from "@/components/Toast";
import {
  authorRoute,
  deletePost,
  setPostLike,
} from "@/api/feed";
import { store } from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type PostAuthorKind =
  | "client"
  | "professional"
  | "establishment";

type PostCardProps = {
  id: string;

  author: {
    id: string;
    /** Cliente: id do perfil com página pública (D-SOC-13). */
    routeId?: string | null;
    name: string;
    avatar?: string | null;
    kind: PostAuthorKind;
    specialty?: string;
  };

  /** Primeira imagem; nula em publicação só de texto (PR 3). */
  image: string | null;

  /** Carrossel até 10 imagens, na ordem escolhida. */
  media?: {
    url: string;
    alt?: string;
  }[];

  likesCount?: number;

  likedByMe?: boolean;

  /** A conta pode remover este post (autoria). */
  mine?: boolean;

  onRemoved?: () => void;

  caption?: string;

  rating?: number;

  service?: {
    id: string;
    name: string;
    price?: number;
    availabilityLabel?: string;
  };

  commentsCount?: number;

  showFollow?: boolean;

  onCommentsPress?: () => void;
  onSharePress?: () => void;
  onMorePress?: () => void;

  testID?: string;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

/**
 * Curtir (PR 3): uma curtida por pessoa, contada no servidor.
 */
export function LikeButton({
  postId,
  initialLiked,
  initialCount,
}: {
  postId: string;
  initialLiked: boolean;
  initialCount: number;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    if (busy) {
      return;
    }

    if (!store.getUser()) {
      router.push("/login");
      return;
    }

    const next = !liked;
    const before = count;
    setLiked(next);
    setCount(Math.max(0, before + (next ? 1 : -1)));
    setBusy(true);

    try {
      const response = await setPostLike(postId, next);
      setLiked(response.liked);
      setCount(response.likesCount);
    } catch (error) {
      setLiked(!next);
      setCount(before);
      toast.show({
        title: "Não foi possível curtir",
        body: error instanceof Error ? error.message : "Tente novamente.",
        icon: "alert-circle",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Curtir, ${count} curtida${count === 1 ? "" : "s"}`}
      accessibilityState={{ selected: liked, busy }}
      hitSlop={6}
      onPress={() => void toggle()}
      style={({ pressed }) => [
        styles.countButton,
        pressed && styles.pressed,
      ]}
    >
      <Icon
        name="heart"
        size={21}
        color={liked ? colors.plum : colors.onSurface}
      />
      <Text style={[styles.countText, liked && styles.countTextActive]}>
        {count}
      </Text>
    </Pressable>
  );
}

export function MediaCarousel({
  media,
  authorName,
  onPress,
}: {
  media: { url: string; alt?: string }[];
  authorName: string;
  onPress: () => void;
}) {
  const styles = useStyles();
  const [width, setWidth] = useState(0);
  const [index, setIndex] = useState(0);
  const total = media.length;

  return (
    <View
      style={styles.mediaPressable}
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
    >
      <ScrollView
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        scrollEnabled={total > 1}
        onMomentumScrollEnd={(event) => {
          if (width > 0) {
            setIndex(Math.round(event.nativeEvent.contentOffset.x / width));
          }
        }}
        accessibilityLabel={
          total > 1
            ? `Carrossel com ${total} imagens de ${authorName}`
            : undefined
        }
      >
        {media.map((item, position) => (
          <Pressable
            key={`${item.url}-${position}`}
            accessibilityRole="button"
            accessibilityLabel={
              item.alt
              || (total > 1
                ? `Imagem ${position + 1} de ${total} publicada por ${authorName}`
                : `Publicação de ${authorName}`)
            }
            onPress={onPress}
            style={{ width: width || undefined }}
          >
            <Image
              source={{ uri: item.url }}
              style={styles.image}
              contentFit="cover"
              transition={220}
            />
          </Pressable>
        ))}
      </ScrollView>

      {total > 1 ? (
        <View style={styles.mediaCount} accessibilityLiveRegion="polite">
          <Text style={styles.mediaCountText}>
            {`${index + 1} de ${total}`}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

export function PostCard({
  id,
  author,
  image,
  media,
  likesCount = 0,
  likedByMe = false,
  mine = false,
  onRemoved,
  caption,
  rating,
  service,
  commentsCount = 0,
  showFollow = true,
  onCommentsPress,
  onSharePress,
  onMorePress,
  testID,
}: PostCardProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [report, setReport] = useState<ReportTarget | null>(null);

  const gallery =
    media && media.length
      ? media
      : image
        ? [{ url: image }]
        : [];

  const profileRoute = authorRoute(author);
  const hasProfile = Boolean(profileRoute);

  const removePost = () => {
    setMenuOpen(false);
    Alert.alert(
      "Remover publicação?",
      "Ela sai do feed e as imagens são apagadas.",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Remover",
          style: "destructive",
          onPress: () => {
            deletePost(id)
              .then(() => {
                toast.show({
                  title: "Publicação removida",
                  icon: "check",
                });
                onRemoved?.();
              })
              .catch((error) => {
                toast.show({
                  title: "Não foi possível remover",
                  body: error instanceof Error ? error.message : "Tente novamente.",
                  icon: "alert-circle",
                });
              });
          },
        },
      ],
    );
  };

  const openMenu = () => {
    if (onMorePress) {
      onMorePress();
      return;
    }

    if (!store.getUser()) {
      router.push("/login");
      return;
    }

    setMenuOpen(true);
  };

  const openAuthor = () => {
    if (!profileRoute) {
      return;
    }

    router.push(profileRoute);
  };

  const openPost = () => {
    router.push(`/post/${id}`);
  };

  const openService = () => {
    if (!service) return;

    router.push(`/service/${service.id}`);
  };

  const openBooking = () => {
    if (!service) return;

    router.push(`/booking/${service.id}`);
  };

  return (
    <View
      testID={testID}
      style={styles.card}
    >
      <View style={styles.header}>
        <Pressable
          accessibilityRole={hasProfile ? "button" : undefined}
          accessibilityLabel={hasProfile ? `Abrir perfil de ${author.name}` : author.name}
          disabled={!hasProfile}
          onPress={openAuthor}
          style={({ pressed }) => [
            styles.authorArea,
            pressed && styles.pressed,
          ]}
        >
          <Avatar
            name={author.name}
            uri={author.avatar}
            size={42}
          />

          <View style={styles.authorText}>
            <Text
              style={styles.authorName}
              numberOfLines={1}
            >
              {author.name}
            </Text>

            {author.specialty ? (
              <Text
                style={styles.authorSubtitle}
                numberOfLines={1}
              >
                {author.specialty}
              </Text>
            ) : null}
          </View>
        </Pressable>

        <View style={styles.headerActions}>
          {showFollow && author.kind !== "client" ? (
            <FollowButton
              id={author.id}
              targetType={author.kind}
              authorName={author.name}
            />
          ) : null}

          {(
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Mais opções da publicação"
              hitSlop={8}
              onPress={openMenu}
              style={({ pressed }) => [
                styles.iconButton,
                pressed && styles.pressed,
              ]}
            >
              <Icon
                name="more-horizontal"
                size={20}
                color={colors.onSurfaceSecondary}
              />
            </Pressable>
          )}
        </View>
      </View>

      {gallery.length ? (
        <MediaCarousel
          media={gallery}
          authorName={author.name}
          onPress={openPost}
        />
      ) : caption ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Abrir publicação"
          onPress={openPost}
          style={({ pressed }) => [
            styles.textPost,
            pressed && styles.pressed,
          ]}
        >
          <Text style={styles.textPostBody}>{caption}</Text>
        </Pressable>
      ) : null}

      <View style={styles.actions}>
        <View style={styles.leftActions}>
          <LikeButton
            postId={id}
            initialLiked={likedByMe}
            initialCount={likesCount}
          />

          <FavoriteButton
            kind="posts"
            id={id}
          />

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={
              commentsCount > 0
                ? `${commentsCount} comentários`
                : "Ver comentários"
            }
            hitSlop={6}
            onPress={
              onCommentsPress ??
              openPost
            }
            style={({ pressed }) => [
              styles.iconButton,
              pressed && styles.pressed,
            ]}
          >
            <Icon
              name="message-circle"
              size={21}
              color={colors.onSurface}
            />
            <Text style={styles.countText}>{commentsCount}</Text>
          </Pressable>

          {onSharePress ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Compartilhar publicação"
              hitSlop={6}
              onPress={onSharePress}
              style={({ pressed }) => [
                styles.iconButton,
                pressed && styles.pressed,
              ]}
            >
              <Icon
                name="send"
                size={20}
                color={colors.onSurface}
              />
            </Pressable>
          ) : null}
        </View>

        {typeof rating === "number" ? (
          <Rating value={rating} />
        ) : null}
      </View>

      {caption && gallery.length ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Abrir publicação completa"
          onPress={openPost}
          style={({ pressed }) => [
            styles.captionPressable,
            pressed && styles.pressed,
          ]}
        >
          <Text
            style={styles.caption}
            numberOfLines={3}
          >
            <Text style={styles.captionAuthor}>
              {author.name}{" "}
            </Text>

            {caption}
          </Text>
        </Pressable>
      ) : null}

      {commentsCount > 0 ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Ver os ${commentsCount} comentários`}
          onPress={
            onCommentsPress ??
            openPost
          }
          style={({ pressed }) => [
            styles.commentsLink,
            pressed && styles.pressed,
          ]}
        >
          <Text style={styles.commentsText}>
            Ver{" "}
            {commentsCount === 1
              ? "1 comentário"
              : `${commentsCount} comentários`}
          </Text>
        </Pressable>
      ) : null}

      {service ? (
        <View style={styles.serviceBox}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Abrir serviço ${service.name}`}
            onPress={openService}
            style={({ pressed }) => [
              styles.serviceInfo,
              pressed && styles.pressed,
            ]}
          >
            <Text
              style={styles.serviceEyebrow}
              numberOfLines={1}
            >
              SERVIÇO
            </Text>

            <Text
              style={styles.serviceName}
              numberOfLines={1}
            >
              {service.name}
            </Text>

            <View style={styles.serviceMeta}>
              {typeof service.price === "number" ? (
                <Text style={styles.servicePrice}>
                  {formatCurrency(
                    service.price,
                  )}
                </Text>
              ) : null}

              {service.availabilityLabel ? (
                <>
                  <View
                    style={
                      styles.serviceSeparator
                    }
                  />

                  <Text
                    style={
                      styles.availability
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
          </Pressable>

          {/* DEC-ID-037: Agendar só com disponibilidade real; sem ela, o
              cartão leva ao serviço. */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={
              service.availabilityLabel
                ? `Agendar ${service.name}`
                : `Ver serviço ${service.name}`
            }
            onPress={service.availabilityLabel ? openBooking : openService}
            style={({ pressed }) => [
              styles.bookButton,
              pressed &&
                styles.bookButtonPressed,
            ]}
          >
            <Text style={styles.bookText}>
              {service.availabilityLabel ? "Agendar" : "Ver serviço"}
            </Text>

            <Icon
              name="arrow-right"
              size={14}
              color={
                colors.onBrandPrimary
              }
            />
          </Pressable>
        </View>
      ) : null}

      <Modal
        visible={menuOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setMenuOpen(false)}
      >
        <Pressable
          accessibilityLabel="Fechar menu"
          style={styles.menuBackdrop}
          onPress={() => setMenuOpen(false)}
        >
          <View style={styles.menuSheet} accessibilityViewIsModal>
            {mine ? (
              <Pressable
                accessibilityRole="button"
                onPress={removePost}
                style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
              >
                <Icon name="trash-2" size={18} color={colors.error} />
                <Text style={styles.menuText}>Remover publicação</Text>
              </Pressable>
            ) : (
              <Pressable
                accessibilityRole="button"
                onPress={() => {
                  setMenuOpen(false);
                  setReport({ type: "post", id });
                }}
                style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
              >
                <Icon name="flag" size={18} color={colors.onSurface} />
                <Text style={styles.menuText}>Denunciar publicação</Text>
              </Pressable>
            )}
            <Pressable
              accessibilityRole="button"
              onPress={() => setMenuOpen(false)}
              style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
            >
              <Icon name="x" size={18} color={colors.muted} />
              <Text style={styles.menuText}>Cancelar</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>

      <ReportModal
        target={report}
        onClose={() => setReport(null)}
      />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  countButton: {
    minHeight: touch.minimum,
    minWidth: touch.minimum,
    paddingHorizontal: spacing.xs,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.xs,
  },

  countText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: 13,
  },

  countTextActive: {
    color: colors.plum,
  },

  mediaCount: {
    position: "absolute",
    top: spacing.md,
    right: spacing.md,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.overlayInk,
  },

  mediaCountText: {
    color: colors.white,
    fontFamily: fonts.sansSemiBold,
    fontSize: 12,
  },

  textPost: {
    marginHorizontal: spacing.lg,
    padding: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
  },

  textPostBody: {
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 17,
    lineHeight: 25,
  },

  menuBackdrop: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: colors.overlayInk,
  },

  menuSheet: {
    padding: spacing.lg,
    gap: spacing.xs,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    backgroundColor: colors.surfaceSecondary,
  },

  menuItem: {
    minHeight: touch.minimum + 4,
    paddingHorizontal: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    borderRadius: radius.sm,
  },

  menuText: {
    color: colors.onSurface,
    fontFamily: fonts.sansMedium,
    fontSize: 16,
  },

  card: {
    width: "100%",
    backgroundColor:
      colors.surface,
    paddingBottom:
      spacing.lg,
  },

  header: {
    minHeight: 66,
    paddingHorizontal:
      spacing.lg,

    flexDirection: "row",
    alignItems: "center",
    justifyContent:
      "space-between",

    gap: spacing.sm,
  },

  authorArea: {
    flex: 1,
    minWidth: 0,

    flexDirection: "row",
    alignItems: "center",
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
    marginTop: 1,

    color:
      colors.muted,

    fontFamily:
      fonts.sans,

    fontSize: 11,
    lineHeight: 14,
  },

  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },

  mediaPressable: {
    width: "100%",
    aspectRatio: 4 / 5,
    backgroundColor:
      colors.surfaceTertiary,
  },

  mediaPressed: {
    opacity: 0.94,
  },

  image: {
    width: "100%",
    height: "100%",
  },

  actions: {
    minHeight: 52,

    paddingHorizontal:
      spacing.sm,

    flexDirection: "row",
    alignItems: "center",
    justifyContent:
      "space-between",
  },

  leftActions: {
    flexDirection: "row",
    alignItems: "center",
  },

  iconButton: {
    width: touch.minimum,
    height: touch.minimum,

    alignItems: "center",
    justifyContent: "center",
  },

  captionPressable: {
    paddingHorizontal:
      spacing.lg,
  },

  caption: {
    color:
      colors.onSurfaceSecondary,

    fontFamily:
      fonts.sans,

    fontSize: 13,
    lineHeight: 19,
  },

  captionAuthor: {
    color:
      colors.onSurface,

    fontFamily:
      fonts.sansSemiBold,
  },

  commentsLink: {
    alignSelf:
      "flex-start",

    paddingHorizontal:
      spacing.lg,

    paddingTop:
      spacing.sm,

    minHeight: 32,

    justifyContent:
      "center",
  },

  commentsText: {
    color:
      colors.muted,

    fontFamily:
      fonts.sans,

    fontSize: 12,
    lineHeight: 16,
  },

  serviceBox: {
    marginTop:
      spacing.md,

    marginHorizontal:
      spacing.lg,

    minHeight: 76,

    padding:
      spacing.md,

    borderRadius:
      radius.md,

    backgroundColor:
      colors.surfaceSecondary,

    borderWidth: 1,
    borderColor:
      colors.glassBorder,

    flexDirection: "row",
    alignItems: "center",

    gap: spacing.md,
  },

  serviceInfo: {
    flex: 1,
    minWidth: 0,
  },

  serviceEyebrow: {
    color:
      colors.plum,

    fontFamily:
      fonts.sansMedium,

    fontSize: 9,
    lineHeight: 12,

    letterSpacing: 0.8,
  },

  serviceName: {
    marginTop: 2,

    color:
      colors.onSurface,

    fontFamily:
      fonts.sansMedium,

    fontSize: 13,
    lineHeight: 17,
  },

  serviceMeta: {
    marginTop:
      spacing.xs,

    minWidth: 0,

    flexDirection: "row",
    alignItems: "center",

    gap: spacing.sm,
  },

  servicePrice: {
    flexShrink: 0,

    color:
      colors.onSurfaceSecondary,

    fontFamily:
      fonts.sansMedium,

    fontSize: 11,
    lineHeight: 14,
  },

  serviceSeparator: {
    width: 3,
    height: 3,

    borderRadius: 2,

    backgroundColor:
      colors.muted,
  },

  availability: {
    flex: 1,

    color:
      colors.plum,

    fontFamily:
      fonts.sansMedium,

    fontSize: 11,
    lineHeight: 14,
  },

  bookButton: {
    minHeight:
      touch.minimum,

    paddingHorizontal:
      spacing.md,

    borderRadius:
      radius.pill,

    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",

    gap: spacing.xs,

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

    fontSize: 12,
    lineHeight: 16,
  },

  pressed: {
    opacity: 0.78,
  },
}));