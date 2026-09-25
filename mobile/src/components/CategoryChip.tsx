import React from "react";
import { Pressable, Text } from "react-native";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type CategoryChipProps = {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  disabled?: boolean;
  testID?: string;
};

export function CategoryChip({
  label,
  selected = false,
  onPress,
  disabled = false,
  testID,
}: CategoryChipProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{
        selected,
        disabled,
      }}
      disabled={disabled}
      hitSlop={4}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        selected
          ? styles.selected
          : styles.unselected,
        disabled && styles.disabled,
        pressed &&
          !disabled &&
          styles.pressed,
      ]}
    >
      <Text
        style={[
          styles.label,
          {
            color: selected
              ? colors.onBrandPrimary
              : colors.onSurfaceSecondary,
          },
        ]}
        numberOfLines={1}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  base: {
    minHeight: touch.minimum,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.pill,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  selected: {
    backgroundColor: colors.plum,
    borderColor: colors.plum,
  },

  unselected: {
    backgroundColor: colors.glassSoft,
    borderColor: colors.glassBorder,
  },

  disabled: {
    opacity: 0.4,
  },

  pressed: {
    opacity: 0.82,
  },

  label: {
    fontFamily: fonts.sansMedium,
    fontSize: 13,
    lineHeight: 17,
    letterSpacing: 0.1,
  },
}));