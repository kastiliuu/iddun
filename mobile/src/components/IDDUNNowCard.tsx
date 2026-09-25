import React from "react";
import {
  Pressable,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";

import { Avatar } from "@/components/Avatar";
import { AvailabilityBadge } from "@/components/AvailabilityBadge";
import { Icon } from "@/components/Icon";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type IDDUNNowCardProps = {
  serviceId: string;
  professionalId: string;
  professionalName: string;
  professionalAvatar?: string | null;

  serviceName: string;
  image?: string | null;

  price?: number;
  timeLabel: string;

  location?: string;

  routeType?: "professional" | "establishment";
  urgent?: boolean;

  testID?: string;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export function IDDUNNowCard({
  serviceId,
  professionalId,
  professionalName,
  professionalAvatar,
  serviceName,
  image,
  price,
  timeLabel,
  location,
  routeType = "professional",
  urgent = true,
  testID,
}: IDDUNNowCardProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const handleOpenService = () => {
    router.push(`/service/${serviceId}`);
  };

  const handleOpenProfile = () => {
    router.push(
      routeType === "establishment"
        ? `/establishment/${professionalId}`
        : `/professional/${professionalId}`,
    );
  };

  return (
    <View
      testID={testID}
      style={styles.card}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Abrir ${serviceName} disponível ${timeLabel}`}
        onPress={handleOpenService}
        style={({ pressed }) => [
          styles.mediaArea,
          pressed && styles.pressed,
        ]}
      >
        {image ? (
          <Image
            source={{ uri: image }}
            style={styles.image}
            contentFit="cover"
            transition={180}
            accessibilityLabel={`Imagem do serviço ${serviceName}`}
          />
        ) : (
          <LinearGradient
            colors={[
              colors.deepViolet,
              colors.surfaceTertiary,
            ]}
            style={styles.imageFallback}
          >
            <Icon
              name="clock"
              size={26}
              color={colors.plum}
            />
          </LinearGradient>
        )}

        <LinearGradient
          pointerEvents="none"
          colors={[
            "transparent",
            colors.overlayInk,
            colors.overlayInkHeavy,
          ]}
          locations={[0.25, 0.7, 1]}
          style={styles.overlay}
        />

        <View style={styles.badgeWrap}>
          <AvailabilityBadge
            label={timeLabel}
            urgent={urgent}
          />
        </View>

        <View style={styles.mediaContent}>
          <Text
            style={styles.serviceName}
            numberOfLines={2}
          >
            {serviceName}
          </Text>

          <View style={styles.bottomRow}>
            {location ? (
              <View style={styles.locationRow}>
                <Icon
                  name="map-pin"
                  size={12}
                  color={colors.onSurfaceSecondary}
                />

                <Text
                  style={styles.location}
                  numberOfLines={1}
                >
                  {location}
                </Text>
              </View>
            ) : (
              <View />
            )}

            {typeof price === "number" ? (
              <Text style={styles.price}>
                {formatCurrency(price)}
              </Text>
            ) : null}
          </View>
        </View>
      </Pressable>

      <View style={styles.profileBar}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Abrir perfil de ${professionalName}`}
          onPress={handleOpenProfile}
          style={({ pressed }) => [
            styles.profilePressable,
            pressed && styles.pressed,
          ]}
        >
          <Avatar
            name={professionalName}
            uri={professionalAvatar}
            size={36}
          />

          <View style={styles.profileText}>
            <Text
              style={styles.professionalName}
              numberOfLines={1}
            >
              {professionalName}
            </Text>

            <Text style={styles.nowLabel}>
              IDDUN Now
            </Text>
          </View>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Agendar ${serviceName}`}
          onPress={() =>
            router.push(
              `/booking/${serviceId}`,
            )
          }
          style={({ pressed }) => [
            styles.bookButton,
            pressed && styles.bookPressed,
          ]}
        >
          <Text style={styles.bookText}>
            Agendar
          </Text>

          <Icon
            name="arrow-right"
            size={14}
            color={colors.onBrandPrimary}
          />
        </Pressable>
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: {
    width: 290,
    overflow: "hidden",
    borderRadius: radius.lg,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  mediaArea: {
    width: "100%",
    height: 260,
    position: "relative",
    overflow: "hidden",
    backgroundColor: colors.surfaceTertiary,
  },

  image: {
    width: "100%",
    height: "100%",
  },

  imageFallback: {
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

  badgeWrap: {
    position: "absolute",
    top: spacing.md,
    left: spacing.md,
  },

  mediaContent: {
    position: "absolute",
    left: spacing.lg,
    right: spacing.lg,
    bottom: spacing.lg,
  },

  serviceName: {
    maxWidth: 220,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 24,
    lineHeight: 29,
  },

  bottomRow: {
    marginTop: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
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
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 11,
    lineHeight: 14,
  },

  price: {
    flexShrink: 0,
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 14,
    lineHeight: 18,
  },

  profileBar: {
    minHeight: 70,
    paddingHorizontal: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
  },

  profilePressable: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
  },

  profileText: {
    flex: 1,
    minWidth: 0,
    marginLeft: spacing.sm,
  },

  professionalName: {
    color: colors.onSurface,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
    lineHeight: 16,
  },

  nowLabel: {
    marginTop: 1,
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 10,
    lineHeight: 13,
    letterSpacing: 0.4,
  },

  bookButton: {
    minHeight: touch.minimum,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.xs,
    backgroundColor: colors.plum,
  },

  bookText: {
    color: colors.onBrandPrimary,
    fontFamily: fonts.sansSemiBold,
    fontSize: 12,
    lineHeight: 16,
  },

  pressed: {
    opacity: 0.86,
  },

  bookPressed: {
    opacity: 0.82,
  },
}));