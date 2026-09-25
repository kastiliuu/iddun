import React from "react";
import {
  Pressable,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import { AvailabilityBadge } from "@/components/AvailabilityBadge";
import { FavoriteButton } from "@/components/FavoriteButton";
import { Icon } from "@/components/Icon";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";

type ServiceCardProps = {
  id: string;
  name: string;
  image?: string | null;

  category?: string;
  professionalName?: string;
  location?: string;

  durationMinutes?: number;
  price?: number;

  availableLabel?: string;
  urgent?: boolean;

  compact?: boolean;
  testID?: string;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

function formatDuration(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (remainingMinutes === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remainingMinutes}min`;
}

export function ServiceCard({
  id,
  name,
  image,
  category,
  professionalName,
  location,
  durationMinutes,
  price,
  availableLabel,
  urgent = false,
  compact = false,
  testID,
}: ServiceCardProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const handlePress = () => {
    router.push(`/service/${id}`);
  };

  return (
    <View
      testID={testID}
      style={[
        styles.card,
        compact && styles.cardCompact,
      ]}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Abrir serviço ${name}`}
        onPress={handlePress}
        style={({ pressed }) => [
          styles.mainArea,
          pressed && styles.pressed,
        ]}
      >
        <View
          style={[
            styles.imageWrap,
            compact && styles.imageWrapCompact,
          ]}
        >
          {image ? (
            <Image
              source={{ uri: image }}
              style={styles.image}
              contentFit="cover"
              transition={180}
              accessibilityLabel={`Imagem do serviço ${name}`}
            />
          ) : (
            <View style={styles.imageFallback}>
              <Icon
                name="scissors"
                size={22}
                color={colors.plum}
              />
            </View>
          )}
        </View>

        <View style={styles.content}>
          {category ? (
            <Text
              style={styles.category}
              numberOfLines={1}
            >
              {category}
            </Text>
          ) : null}

          <Text
            style={[
              styles.name,
              compact && styles.nameCompact,
            ]}
            numberOfLines={2}
          >
            {name}
          </Text>

          {professionalName ? (
            <Text
              style={styles.professional}
              numberOfLines={1}
            >
              {professionalName}
            </Text>
          ) : null}

          <View style={styles.metaRow}>
            {typeof durationMinutes === "number" ? (
              <View style={styles.metaItem}>
                <Icon
                  name="clock"
                  size={12}
                  color={colors.muted}
                />

                <Text style={styles.metaText}>
                  {formatDuration(durationMinutes)}
                </Text>
              </View>
            ) : null}

            {location ? (
              <View style={styles.metaItem}>
                <Icon
                  name="map-pin"
                  size={12}
                  color={colors.muted}
                />

                <Text
                  style={styles.metaText}
                  numberOfLines={1}
                >
                  {location}
                </Text>
              </View>
            ) : null}
          </View>

          <View style={styles.footer}>
            {typeof price === "number" ? (
              <Text style={styles.price}>
                {formatCurrency(price)}
              </Text>
            ) : (
              <View />
            )}

            {availableLabel ? (
              <AvailabilityBadge
                label={availableLabel}
                urgent={urgent}
              />
            ) : null}
          </View>
        </View>
      </Pressable>

      <View style={styles.favoriteWrap}>
        <FavoriteButton
          kind="services"
          id={id}
          size={20}
        />
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: {
    width: "100%",
    minHeight: 150,
    borderRadius: radius.md,
    overflow: "hidden",
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  cardCompact: {
    minHeight: 126,
  },

  mainArea: {
    flexDirection: "row",
    padding: spacing.md,
  },

  pressed: {
    opacity: 0.84,
  },

  imageWrap: {
    width: 112,
    height: 126,
    borderRadius: radius.md,
    overflow: "hidden",
    backgroundColor: colors.surfaceTertiary,
    flexShrink: 0,
  },

  imageWrapCompact: {
    width: 88,
    height: 104,
  },

  image: {
    width: "100%",
    height: "100%",
  },

  imageFallback: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.plumSoft,
  },

  content: {
    flex: 1,
    minWidth: 0,
    paddingLeft: spacing.md,
    paddingRight: spacing.xl,
  },

  category: {
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },

  name: {
    marginTop: 3,
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 16,
    lineHeight: 21,
  },

  nameCompact: {
    fontSize: 14,
    lineHeight: 19,
  },

  professional: {
    marginTop: spacing.xs,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 12,
    lineHeight: 16,
  },

  metaRow: {
    marginTop: spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: spacing.md,
  },

  metaItem: {
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },

  metaText: {
    flexShrink: 1,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 11,
    lineHeight: 14,
  },

  footer: {
    marginTop: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
  },

  price: {
    flexShrink: 0,
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 14,
    lineHeight: 18,
  },

  favoriteWrap: {
    position: "absolute",
    top: spacing.sm,
    right: spacing.sm,
  },
}));