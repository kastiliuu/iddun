import React from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  View,
  ViewStyle,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "outline";

type ButtonProps = {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  compact?: boolean;
  testID?: string;
  accessibilityLabel?: string;
  style?: ViewStyle;
};

export function Button({
  title,
  onPress,
  variant = "primary",
  disabled = false,
  loading = false,
  fullWidth = false,
  compact = false,
  testID,
  accessibilityLabel,
  style,
}: ButtonProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  const isDisabled =
    disabled || loading;

  const handlePress = () => {
    if (isDisabled) {
      return;
    }

    Haptics.impactAsync(
      Haptics.ImpactFeedbackStyle.Light,
    ).catch(() => {});

    onPress?.();
  };

  const textColor =
    variant === "primary"
      ? colors.onBrandPrimary
      : variant === "secondary"
        ? colors.onSurface
        : variant === "outline"
          ? colors.onSurface
          : colors.plum;

  const spinnerColor =
    textColor;

  const content = (
    <>
      {loading ? (
        <ActivityIndicator
          size="small"
          color={spinnerColor}
          accessibilityLabel="Carregando"
        />
      ) : null}

      <Text
        style={[
          styles.text,
          compact &&
            styles.textCompact,
          {
            color: textColor,
          },
        ]}
        numberOfLines={1}
      >
        {title}
      </Text>
    </>
  );

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={
        accessibilityLabel ??
        title
      }
      accessibilityState={{
        disabled: isDisabled,
        busy: loading,
      }}
      disabled={isDisabled}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.base,

        compact
          ? styles.compact
          : styles.regular,

        fullWidth &&
          styles.fullWidth,

        variant ===
          "secondary" &&
          styles.secondary,

        variant ===
          "outline" &&
          styles.outline,

        variant ===
          "ghost" &&
          styles.ghost,

        isDisabled &&
          styles.disabled,

        pressed &&
          !isDisabled && {
            opacity: 0.88,
            transform: [
              {
                scale: 0.985,
              },
            ],
          },

        style,
      ]}
    >
      {variant ===
      "primary" ? (
        <>
          <LinearGradient
            colors={[
              colors.plum,
              colors.deepViolet,
            ]}
            start={{
              x: 0,
              y: 0,
            }}
            end={{
              x: 1,
              y: 1,
            }}
            style={
              styles.primaryBackground
            }
          />

          <View
            style={
              styles.content
            }
          >
            {content}
          </View>
        </>
      ) : (
        <View
          style={styles.content}
        >
          {content}
        </View>
      )}
    </Pressable>
  );
}

const useStyles = makeStyles(
  (colors) => ({
    base: {
      position: "relative",

      overflow: "hidden",

      borderRadius:
        radius.pill,

      alignItems: "center",

      justifyContent:
        "center",
    },

    regular: {
      minHeight: 52,

      paddingHorizontal:
        spacing.xl,

      paddingVertical:
        spacing.md,
    },

    compact: {
      minHeight:
        touch.minimum,

      paddingHorizontal:
        spacing.lg,

      paddingVertical:
        spacing.sm,
    },

    fullWidth: {
      width: "100%",
    },

    primaryBackground: {
      position: "absolute",

      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
    },

    content: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "center",

      gap: spacing.sm,
    },

    secondary: {
      backgroundColor:
        colors.surfaceTertiary,

      borderWidth: 1,

      borderColor:
        colors.border,
    },

    outline: {
      backgroundColor:
        "transparent",

      borderWidth: 1,

      borderColor:
        colors.border,
    },

    ghost: {
      backgroundColor:
        "transparent",
    },

    disabled: {
      opacity: 0.45,
    },

    text: {
      fontFamily:
        fonts.sansMedium,

      fontSize: 14,

      lineHeight: 18,

      letterSpacing: 0.3,

      textAlign: "center",
    },

    textCompact: {
      fontSize: 13,

      lineHeight: 17,
    },
  }),
);