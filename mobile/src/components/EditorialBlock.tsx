import React from "react";
import {
  Pressable,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";

import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  useTheme,
} from "@/theme";

type EditorialBlockProps = {
  title: string;
  subtitle?: string;
  image?: string | null;

  eyebrow?: string;
  actionLabel?: string;

  onPress?: () => void;

  testID?: string;
};

export function EditorialBlock({
  title,
  subtitle,
  image,
  eyebrow,
  actionLabel = "Explorar",
  onPress,
  testID,
}: EditorialBlockProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  return (
    <Pressable
      testID={testID}
      accessibilityRole={
        onPress ? "button" : undefined
      }
      accessibilityLabel={
        onPress
          ? `${title}. ${actionLabel}`
          : title
      }
      disabled={!onPress}
      onPress={onPress}
      style={({ pressed }) => [
        styles.container,
        pressed &&
          onPress &&
          styles.pressed,
      ]}
    >
      {image ? (
        <Image
          source={{ uri: image }}
          style={styles.image}
          contentFit="cover"
          transition={220}
          accessibilityLabel={`Imagem editorial: ${title}`}
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
          <Text
            accessible={false}
            style={styles.fallbackSpark}
          >
            {SPARK}
          </Text>
        </LinearGradient>
      )}

      <LinearGradient
        pointerEvents="none"
        colors={[
          "transparent",
          colors.overlayInkSoft,
          colors.overlayInkStrong,
          colors.overlayInkHeavy,
        ]}
        locations={[
          0.1,
          0.45,
          0.75,
          1,
        ]}
        style={styles.overlay}
      />

      <View style={styles.content}>
        {eyebrow ? (
          <View style={styles.eyebrowRow}>
            <Text
              accessible={false}
              style={styles.spark}
            >
              {SPARK}
            </Text>

            <Text
              style={styles.eyebrow}
              numberOfLines={1}
            >
              {eyebrow}
            </Text>
          </View>
        ) : null}

        <Text
          style={styles.title}
          numberOfLines={3}
        >
          {title}
        </Text>

        {subtitle ? (
          <Text
            style={styles.subtitle}
            numberOfLines={3}
          >
            {subtitle}
          </Text>
        ) : null}

        {onPress ? (
          <View style={styles.actionRow}>
            <Text style={styles.actionText}>
              {actionLabel}
            </Text>

            <Icon
              name="arrow-up-right"
              size={15}
              color={colors.onSurface}
            />
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    width: "100%",
    height: 360,
    position: "relative",
    overflow: "hidden",

    borderRadius: radius.lg,

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

  fallbackSpark: {
    color: colors.plum,

    fontFamily:
      fonts.display,
    fontSize: 42,
    lineHeight: 50,
    opacity: 0.8,
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

    left: spacing.xl,
    right: spacing.xl,
    bottom: spacing.xl,
  },

  eyebrowRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,

    marginBottom:
      spacing.sm,
  },

  spark: {
    color: colors.plum,

    fontFamily:
      fonts.sansSemiBold,

    fontSize: 12,
    lineHeight: 16,
  },

  eyebrow: {
    flexShrink: 1,

    color:
      colors.onSurfaceSecondary,

    fontFamily:
      fonts.sansMedium,

    fontSize: 11,
    lineHeight: 15,

    letterSpacing: 1,
    textTransform: "uppercase",
  },

  title: {
    maxWidth: 300,

    color:
      colors.onSurface,

    fontFamily:
      fonts.display,

    fontSize: 30,
    lineHeight: 35,

    letterSpacing: -0.3,
  },

  subtitle: {
    maxWidth: 300,

    marginTop:
      spacing.sm,

    color:
      colors.onSurfaceSecondary,

    fontFamily:
      fonts.sans,

    fontSize: 13,
    lineHeight: 19,
  },

  actionRow: {
    alignSelf: "flex-start",

    marginTop:
      spacing.lg,

    minHeight: 44,

    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },

  actionText: {
    color:
      colors.onSurface,

    fontFamily:
      fonts.sansMedium,

    fontSize: 13,
    lineHeight: 17,
  },

  pressed: {
    opacity: 0.9,
  },
}));