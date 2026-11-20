import React from "react";
import { Pressable, Text } from "react-native";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";

import { Avatar } from "@/components/Avatar";
import { Icon } from "@/components/Icon";
import { store, useStoreVersion } from "@/store/local";
import {
  designScale,
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

/**
 * DS-V1-01-D02 + QA-001: avatar pessoal único e área de trabalho atual.
 * "Minha conta" identifica a pessoa; nomes de empresas identificam páginas.
 * Tocar abre ferramentas, sem criar conta nem mudar permissão.
 * Nome longo é cortado só na tela: o leitor de tela recebe o nome inteiro.
 */
export function ContextPill({ label }: { label: string }) {
  useStoreVersion();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const user = store.getUser();

  if (!user) {
    return null;
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Áreas da conta: ${label}`}
      accessibilityHint="Abre ferramentas e estabelecimentos autorizados"
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        router.push("/contexts");
      }}
      style={({ pressed }) => [styles.pill, pressed && styles.pressed]}
      testID="context-pill"
    >
      <Avatar name={user.name} uri={user.avatar} size={28} />
      <Text style={styles.label} numberOfLines={1}>
        {label}
      </Text>
      <Icon name="chevron-down" size={16} color={colors.muted} />
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  pill: {
    minHeight: touch.minimum,
    maxWidth: "100%",
    flexShrink: 1,
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingLeft: spacing.sm,
    paddingRight: spacing.md,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    backgroundColor: colors.glassSoft,
  },

  pressed: {
    opacity: 0.82,
  },

  label: {
    flexShrink: 1,
    color: colors.onSurface,
    fontFamily: fonts.sansMedium,
    fontSize: designScale.typography.secondary,
  },
}));
