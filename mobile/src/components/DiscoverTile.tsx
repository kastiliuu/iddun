import React from "react";
import {
  Pressable,
  StyleProp,
  Text,
  View,
  ViewStyle,
} from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";

import { Icon } from "@/components/Icon";
import { Rating } from "@/components/Rating";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";

type DiscoverTileType =
  | "post"
  | "professional"
  | "establishment"
  | "service";

type DiscoverTileProps = {
  id: string;
  type: DiscoverTileType;

  title: string;
  subtitle?: string;

  image?: string | null;

  rating?: number;
  location?: string;

  height?: number;

  style?: StyleProp<ViewStyle>;
  testID?: string;
};

export function DiscoverTile({
  id,
  type,
  title,
  subtitle,
  image,
  rating,
  location,
  height = 260,
  style,
  testID,
}: DiscoverTileProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const handlePress = () => {
    switch (type) {
      case "professional":
        router.push(`/professional/${id}`);
        break;

      case "establishment":
        router.push(`/establishment/${id}`);
        break;

      case "service":
        router.push(`/service/${id}`);
        break;

      case "post":
      default:
        router.push(`/post/${id}`);
        break;
    }
  };

  const getTypeLabel = () => {
    switch (type) {
      case "professional":
        return "Profissional";

      case "establishment":
        return "Estabelecimento";

      case "service":
        return "Serviço";

      case "post":
      default:
        return null;
    }
  };

  const typeLabel = getTypeLabel();

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`Abrir ${title}`}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.container,
        {
          height,
        },
        pressed && styles.pressed,
        style,
      ]}
    >
      {image ? (
        <Image
          source={{ uri: image }}
          style={styles.image}
          contentFit="cover"
          transition={200}
          accessibilityLabel={`Imagem de ${title}`}
        />
      ) : (
        <LinearGradient
          colors={[
            colors.deepViolet,
            colors.surfaceTertiary,
          ]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.fallback}
        >
          <Icon
            name={
              type === "service"
                ? "scissors"
                : type === "professional"
                  ? "user"
                  : type === "establishment"
                    ? "home"
                    : "image"
            }
            size={26}
            color={colors.plum}
          />
        </LinearGradient>
      )}

      <LinearGradient
        pointerEvents="none"
        colors={[
          "transparent",
          colors.overlayInkSoft,
          colors.overlayInkStrong,
        ]}
        locations={[0.25, 0.62, 1]}
        style={styles.overlay}
      />

      <View style={styles.content}>
        {typeLabel ? (
          <View style={styles.typeBadge}>
            <Text style={styles.typeText}>
              {typeLabel}
            </Text>
          </View>
        ) : null}

        <Text
          style={styles.title}
          numberOfLines={2}
        >
          {title}
        </Text>

        {subtitle ? (
          <Text
            style={styles.subtitle}
            numberOfLines={2}
          >
            {subtitle}
          </Text>
        ) : null}

        {(rating !== undefined || location) ? (
          <View style={styles.metaRow}>
            {rating !== undefined ? (
              <Rating
                value={rating}
                small
              />
            ) : null}

            {rating !== undefined && location ? (
              <View style={styles.separator} />
            ) : null}

            {location ? (
              <View style={styles.locationRow}>
                <Icon
                  name="map-pin"
                  size={11}
                  color={colors.onSurfaceSecondary}
                />

                <Text
                  style={styles.location}
                  numberOfLines={1}
                >
                  {location}
                </Text>
              </View>
            ) : null}
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    width: "100%",
    position: "relative",
    overflow: "hidden",

    borderRadius: radius.md,

    backgroundColor:
      colors.surfaceSecondary,

    borderWidth: 1,
    borderColor:
      colors.glassBorder,
  },

  image: {
    width: "100%",
    height: "100%",
  },

  fallback: {
    width: "100%",
    height: "100%",
    alignItems: "center",
    justifyContent: "center",
  },

  overlay: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },

  content: {
    position: "absolute",
    left: spacing.md,
    right: spacing.md,
    bottom: spacing.md,
  },

  typeBadge: {
    alignSelf: "flex-start",

    marginBottom:
      spacing.sm,

    paddingHorizontal:
      spacing.sm,

    paddingVertical: 4,

    borderRadius:
      radius.pill,

    backgroundColor:
      colors.overlayInkStrong,

    borderWidth: 1,
    borderColor:
      colors.glassBorder,
  },

  typeText: {
    color: colors.plum,

    fontFamily:
      fonts.sansMedium,

    fontSize: 9,
    lineHeight: 12,

    letterSpacing: 0.7,
    textTransform: "uppercase",
  },

  title: {
    color:
      colors.onSurface,

    fontFamily:
      fonts.sansSemiBold,

    fontSize: 15,
    lineHeight: 20,
  },

  subtitle: {
    marginTop: 2,

    color:
      colors.onSurfaceSecondary,

    fontFamily:
      fonts.sans,

    fontSize: 11,
    lineHeight: 15,
  },

  metaRow: {
    marginTop:
      spacing.sm,

    minWidth: 0,

    flexDirection: "row",
    alignItems: "center",

    gap: spacing.sm,
  },

  separator: {
    width: 3,
    height: 3,

    borderRadius: 2,

    backgroundColor:
      colors.onSurfaceSecondary,

    opacity: 0.6,
  },

  locationRow: {
    flex: 1,
    minWidth: 0,

    flexDirection: "row",
    alignItems: "center",

    gap: spacing.xs,
  },

  location: {
    flex: 1,

    color:
      colors.onSurfaceSecondary,

    fontFamily:
      fonts.sans,

    fontSize: 10,
    lineHeight: 13,
  },

  pressed: {
    opacity: 0.86,

    transform: [
      {
        scale: 0.985,
      },
    ],
  },
}));