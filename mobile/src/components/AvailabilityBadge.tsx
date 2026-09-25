import React from "react";
import { Text, View } from "react-native";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";

type AvailabilityBadgeProps = {
  label: string;
  urgent?: boolean;
  accessibilityLabel?: string;
};

export function AvailabilityBadge({
  label,
  urgent = false,
  accessibilityLabel,
}: AvailabilityBadgeProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.base,
        urgent ? styles.urgent : styles.default,
      ]}
      accessible
      accessibilityRole="text"
      accessibilityLabel={
        accessibilityLabel ??
        `${urgent ? "Horário com alta procura" : "Horário disponível"}: ${label}`
      }
    >
      <View
        style={[
          styles.dot,
          {
            backgroundColor: urgent
              ? colors.onBrandPrimary
              : colors.plum,
          },
        ]}
      />

      <Text
        style={[
          styles.text,
          urgent ? styles.textUrgent : styles.textDefault,
        ]}
        numberOfLines={1}
      >
        {label}
      </Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  base: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    borderWidth: 1,
  },

  default: {
    backgroundColor: colors.glassSoft,
    borderColor: colors.glassBorder,
  },

  urgent: {
    backgroundColor: colors.plum,
    borderColor: colors.plum,
  },

  dot: {
    width: 5,
    height: 5,
    borderRadius: 3,
  },

  text: {
    fontFamily: fonts.sansMedium,
    fontSize: 11,
    lineHeight: 14,
    letterSpacing: 0.2,
  },

  textDefault: {
    color: colors.onSurfaceSecondary,
  },

  textUrgent: {
    color: colors.onBrandPrimary,
  },
}));