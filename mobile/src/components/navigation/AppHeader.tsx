import React from "react";
import { Pressable, Text, View } from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import { Icon, type IconName } from "@/components/Icon";
import { ContextPill } from "@/components/navigation/ContextPill";
import { store, useStoreVersion } from "@/store/local";
import {
  designScale,
  fonts,
  makeStyles,
  radius,
  spacing,
  ThemeScope,
  touch,
  useTheme,
} from "@/theme";

/** Respiro do topo que as telas já reservam para a barra de status. */
export const HEADER_TOP_INSET = 54;

export type AppHeaderAction = {
  icon: IconName;
  label: string;
  onPress: () => void;
  /** Texto ao lado do ícone (ex.: "Criar"). Sem ele, só o ícone. */
  text?: string;
};

type AppHeaderProps = {
  /** Título funcional no lugar da marca (telas de lista). */
  title?: string;
  /** Uma ação contextual da tela, no máximo. */
  action?: AppHeaderAction;
  /** Não lidas reais; sem o número, o sino aparece sem contador. */
  unreadCount?: number;
  /** Contexto ativo escrito ao lado do avatar (DS-V1-01-D02). */
  contextLabel?: string;
  /** Margem lateral do conteúdo da tela, para a barra ir de borda a borda. */
  bleed?: number;
};

/**
 * Cabeçalho único das telas logadas do app (DS-V1-01-D01 e D02): faixa
 * preta com a marca ou o título, uma ação da tela, o sino e, abaixo, o
 * avatar com a área atual. É preto nos dois temas; o resto da tela
 * segue o tema. A conta pessoal é a mesma nas ferramentas profissionais.
 */
export function AppHeader(props: AppHeaderProps) {
  return (
    <ThemeScope scheme="dark">
      <HeaderBar {...props} />
    </ThemeScope>
  );
}

function HeaderBar({
  title,
  action,
  unreadCount = 0,
  contextLabel = "Minha conta",
  bleed = 0,
}: AppHeaderProps) {
  useStoreVersion();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const user = store.getUser();
  const badge = unreadCount > 9 ? "9+" : String(unreadCount);

  return (
    <View
      style={[
        styles.bar,
        { marginHorizontal: -bleed, paddingHorizontal: bleed || spacing.lg },
      ]}
    >
      <View style={styles.row}>
        {title ? (
          <Text style={styles.title} accessibilityRole="header" numberOfLines={1}>
            {title}
          </Text>
        ) : (
          <Image
            source={require("../../../assets/branding/iddun-logo-white.png")}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />
        )}

        <View style={styles.actions}>
          {action ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={action.label}
              onPress={action.onPress}
              style={({ pressed }) => [
                action.text ? styles.textAction : styles.iconAction,
                pressed && styles.pressed,
              ]}
            >
              <Icon
                name={action.icon}
                size={action.text ? 16 : 20}
                color={action.text ? colors.onBrandPrimary : colors.onSurface}
              />
              {action.text ? (
                <Text style={styles.textActionLabel}>{action.text}</Text>
              ) : null}
            </Pressable>
          ) : null}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={
              unreadCount > 0
                ? `Notificações, ${unreadCount} não lidas`
                : "Notificações"
            }
            onPress={() => router.push("/notifications")}
            style={({ pressed }) => [styles.iconAction, pressed && styles.pressed]}
          >
            <Icon name="bell" size={20} color={colors.onSurface} />
            {unreadCount > 0 ? (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{badge}</Text>
              </View>
            ) : null}
          </Pressable>
        </View>
      </View>

      {user ? (
        <View style={styles.contextRow}>
          <ContextPill label={contextLabel} />
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  bar: {
    marginTop: -HEADER_TOP_INSET,
    paddingTop: HEADER_TOP_INSET,
    paddingBottom: spacing.md,
    marginBottom: spacing.lg,
    gap: spacing.sm,
    backgroundColor: colors.ink,
  },

  row: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },

  logo: {
    width: 112,
    height: 34,
  },

  title: {
    flexShrink: 1,
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: designScale.typography.headingSmall,
  },

  actions: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },

  iconAction: {
    width: touch.minimum,
    height: touch.minimum,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.glassSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  textAction: {
    minHeight: touch.minimum,
    paddingHorizontal: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.plum,
  },

  textActionLabel: {
    color: colors.onBrandPrimary,
    fontFamily: fonts.sansSemiBold,
    fontSize: designScale.typography.secondary,
  },

  pressed: {
    opacity: 0.82,
  },

  badge: {
    position: "absolute",
    top: 4,
    right: 3,
    minWidth: 17,
    height: 17,
    paddingHorizontal: 4,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.plum,
  },

  badgeText: {
    color: colors.onBrandPrimary,
    fontFamily: fonts.sansSemiBold,
    fontSize: designScale.typography.caption,
  },

  contextRow: {
    flexDirection: "row",
  },
}));
