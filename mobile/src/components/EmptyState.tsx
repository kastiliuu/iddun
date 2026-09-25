import React from "react";
import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
} from "@/theme";

type EmptyStateProps = {
  title: string;
  description?: string;
  actionLabel?: string;
  onActionPress?: () => void;
  compact?: boolean;
};

export function EmptyState({
  title,
  description,
  actionLabel,
  onActionPress,
  compact = false,
}: EmptyStateProps) {
  const styles = useStyles();

  return (
    <View
      style={[
        styles.container,
        compact && styles.containerCompact,
      ]}
      accessible
      accessibilityRole="summary"
    >
      <View style={styles.sparkWrap}>
        <Text
          accessible={false}
          style={styles.spark}
        >
          {SPARK}
        </Text>
      </View>

      <Text
        style={[
          styles.title,
          compact && styles.titleCompact,
        ]}
      >
        {title}
      </Text>

      {description ? (
        <Text
          style={[
            styles.description,
            compact && styles.descriptionCompact,
          ]}
        >
          {description}
        </Text>
      ) : null}

      {actionLabel && onActionPress ? (
        <View style={styles.actionWrap}>
          <Button
            title={actionLabel}
            onPress={onActionPress}
            variant="secondary"
            compact
          />
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xxxl,
  },

  containerCompact: {
    paddingVertical: spacing.xxl,
  },

  sparkWrap: {
    width: 48,
    height: 48,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
    backgroundColor: colors.plumSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  spark: {
    color: colors.plum,
    fontFamily: fonts.sansSemiBold,
    fontSize: 20,
    lineHeight: 24,
  },

  title: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 22,
    lineHeight: 28,
    textAlign: "center",
  },

  titleCompact: {
    fontSize: 19,
    lineHeight: 24,
  },

  description: {
    maxWidth: 320,
    marginTop: spacing.sm,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
  },

  descriptionCompact: {
    fontSize: 12,
    lineHeight: 17,
  },

  actionWrap: {
    marginTop: spacing.xl,
  },
}));