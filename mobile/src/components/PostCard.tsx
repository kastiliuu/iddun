import React from "react";
import {
  Pressable,
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
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type PostAuthorKind =
  | "professional"
  | "establishment";

type PostCardProps = {
  id: string;

  author: {
    id: string;
    name: string;
    avatar?: string | null;
    kind: PostAuthorKind;
    specialty?: string;
  };

  image: string;

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

export function PostCard({
  id,
  author,
  image,
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

  const openAuthor = () => {
    router.push(
      author.kind === "establishment"
        ? `/establishment/${author.id}`
        : `/professional/${author.id}`,
    );
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
          accessibilityRole="button"
          accessibilityLabel={`Abrir perfil de ${author.name}`}
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
          {showFollow ? (
            <FollowButton
              id={author.id}
              targetType={author.kind}
              authorName={author.name}
            />
          ) : null}

          {onMorePress ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Mais opções"
              hitSlop={8}
              onPress={onMorePress}
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
          ) : null}
        </View>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Abrir publicação"
        onPress={openPost}
        style={({ pressed }) => [
          styles.mediaPressable,
          pressed && styles.mediaPressed,
        ]}
      >
        <Image
          source={{ uri: image }}
          style={styles.image}
          contentFit="cover"
          transition={220}
          accessibilityLabel={`Publicação de ${author.name}`}
        />
      </Pressable>

      <View style={styles.actions}>
        <View style={styles.leftActions}>
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

      {caption ? (
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

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Agendar ${service.name}`}
            onPress={openBooking}
            style={({ pressed }) => [
              styles.bookButton,
              pressed &&
                styles.bookButtonPressed,
            ]}
          >
            <Text style={styles.bookText}>
              Agendar
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
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
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