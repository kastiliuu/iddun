import React from "react";
import { Pressable, Text, View } from "react-native";

import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type SectionHeaderProps = {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onActionPress?: () => void;
  showSpark?: boolean;
  testID?: string;
};

export function SectionHeader({
  title,
  subtitle,
  actionLabel,
  onActionPress,
  showSpark = false,
  testID,
}: SectionHeaderProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  const hasAction =
    Boolean(actionLabel) &&
    Boolean(onActionPress);

  return (
    <View
      testID={testID}
      style={styles.container}
    >
      <View style={styles.textWrap}>
        <View style={styles.titleRow}>
          {showSpark ? (
            <Text
              accessible={false}
              style={styles.spark}
            >
              ✦
            </Text>
          ) : null}

          <Text
            style={styles.title}
            numberOfLines={1}
          >
            {title}
          </Text>
        </View>

        {subtitle ? (
          <Text
            style={styles.subtitle}
            numberOfLines={2}
          >
            {subtitle}
          </Text>
        ) : null}
      </View>

      {hasAction ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            actionLabel
          }
          hitSlop={6}
          onPress={onActionPress}
          style={({ pressed }) => [
            styles.action,
            pressed &&
              styles.actionPressed,
          ]}
        >
          <Text
            style={styles.actionText}
            numberOfLines={1}
          >
            {actionLabel}
          </Text>

          <Icon
            name="chevron-right"
            size={15}
            color={colors.plum}
          />
        </Pressable>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    width: "100%",
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: spacing.md,
  },

  textWrap: {
    flex: 1,
  },

  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },

  spark: {
    color: colors.plum,
    fontFamily: fonts.sansSemiBold,
    fontSize: 14,
    lineHeight: 18,
  },

  title: {
    flexShrink: 1,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 22,
    lineHeight: 28,
  },

  subtitle: {
    marginTop: spacing.xs,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 12,
    lineHeight: 17,
  },

  action: {
    minHeight: touch.minimum,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
    paddingLeft: spacing.md,
  },

  actionPressed: {
    opacity: 0.7,
  },

  actionText: {
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
    lineHeight: 16,
  },
}));