import React from "react";
import { Text, View } from "react-native";

import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  spacing,
  useTheme,
} from "@/theme";

type RatingProps = {
  value: number;
  small?: boolean;
  showValue?: boolean;
};

export function Rating({
  value,
  small = false,
  showValue = true,
}: RatingProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  const normalizedValue = Math.max(0, Math.min(5, value));

  return (
    <View
      style={styles.row}
      accessible
      accessibilityRole="text"
      accessibilityLabel={`Nota ${normalizedValue.toFixed(1)} de 5`}
    >
      <Icon
        name="star"
        size={small ? 11 : 13}
        color={colors.plum}
      />

      {showValue ? (
        <Text
          style={[
            styles.value,
            small && styles.valueSmall,
          ]}
        >
          {normalizedValue.toFixed(1)}
        </Text>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },

  value: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
    lineHeight: 16,
  },

  valueSmall: {
    fontSize: 11,
    lineHeight: 14,
  },
}));