import React from "react";
import {
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";

import { Icon, type IconName } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

/**
 * Moldura das telas de contexto (PR 1, D-SOC-04): troca de contexto e as
 * ferramentas que já existem no app para Profissional e Estabelecimento.
 * Cada destino continua conferindo a permissão no backend.
 */

export type ContextRowProps = {
  icon: IconName;
  title: string;
  subtitle?: string;
  current?: boolean;
  onPress: () => void;
};

export function ContextRow({
  icon,
  title,
  subtitle,
  current = false,
  onPress,
}: ContextRowProps) {
  const styles = useStyles();
  const { colors } = useTheme();

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}. ${subtitle}` : title}
      accessibilityState={{ selected: current }}
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <View style={styles.rowIcon}>
        <Icon name={icon} size={18} color={colors.plum} />
      </View>
      <View style={styles.rowText}>
        <Text style={styles.rowTitle} numberOfLines={1}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={styles.rowSubtitle} numberOfLines={2}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      <Icon
        name={current ? "check" : "chevron-right"}
        size={18}
        color={current ? colors.plum : colors.muted}
      />
    </Pressable>
  );
}

export function ContextSection({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const styles = useStyles();

  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel} accessibilityRole="header">
        {label}
      </Text>
      <View style={styles.card}>{children}</View>
    </View>
  );
}

export function ContextScreen({
  eyebrow,
  title,
  description,
  notice,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  notice?: string;
  children: React.ReactNode;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() =>
              router.canGoBack() ? router.back() : router.replace("/(tabs)")
            }
            style={({ pressed }) => [
              styles.headerButton,
              pressed && styles.pressed,
            ]}
          >
            <Icon name="arrow-left" size={20} color={colors.onSurface} />
          </Pressable>
        </View>

        <Text style={styles.eyebrow}>{eyebrow}</Text>
        <Text style={styles.title} accessibilityRole="header">
          {title}
        </Text>
        {description ? (
          <Text style={styles.description}>{description}</Text>
        ) : null}
        {notice ? (
          <View style={styles.notice} accessibilityRole="alert">
            <Icon name="alert-circle" size={18} color={colors.warning} />
            <Text style={styles.noticeText}>{notice}</Text>
          </View>
        ) : null}

        {children}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },

  content: {
    paddingTop: 54,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
  },

  header: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
  },

  headerButton: {
    width: touch.minimum,
    height: touch.minimum,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.glassSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  pressed: {
    opacity: 0.82,
  },

  eyebrow: {
    marginTop: spacing.lg,
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
    letterSpacing: 1.4,
  },

  title: {
    marginTop: spacing.sm,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 28,
    lineHeight: 34,
  },

  description: {
    marginTop: spacing.sm,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 14,
    lineHeight: 21,
  },

  notice: {
    marginTop: spacing.md,
    padding: spacing.md,
    flexDirection: "row",
    gap: spacing.sm,
    borderRadius: radius.md,
    backgroundColor: colors.glassSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  noticeText: {
    flex: 1,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 13,
    lineHeight: 19,
  },

  section: {
    marginTop: spacing.xl,
  },

  sectionLabel: {
    marginBottom: spacing.sm,
    color: colors.muted,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
    letterSpacing: 1.2,
  },

  card: {
    overflow: "hidden",
    borderRadius: radius.lg,
    backgroundColor: colors.glassSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  row: {
    minHeight: touch.minimum + 12,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.glassBorder,
  },

  rowIcon: {
    width: 36,
    height: 36,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
  },

  rowText: {
    flex: 1,
    gap: 2,
  },

  rowTitle: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 15,
  },

  rowSubtitle: {
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 12,
    lineHeight: 17,
  },
}));
