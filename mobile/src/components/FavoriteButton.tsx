import React from "react";
import { Pressable } from "react-native";
import * as Haptics from "expo-haptics";
import {
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withSpring,
} from "react-native-reanimated";

import { AnimatedIcon } from "@/components/Icon";
import {
  makeStyles,
  touch,
  useTheme,
} from "@/theme";
import {
  store,
  useStoreVersion,
} from "@/store/local";

export type FavoriteKind =
  | "posts"
  | "professionals"
  | "services";

type FavoriteButtonProps = {
  kind: FavoriteKind;
  id: string;
  size?: number;
  testID?: string;
  accessibilityLabel?: string;
};

export function FavoriteButton({
  kind,
  id,
  size = 22,
  testID,
  accessibilityLabel,
}: FavoriteButtonProps) {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();

  const active = store.isFavorite(kind, id);

  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.get() }],
  }));

  const handlePress = () => {
    Haptics.impactAsync(
      Haptics.ImpactFeedbackStyle.Medium,
    ).catch(() => {});

    scale.set(withSequence(
      withSpring(1.28, {
        damping: 7,
        stiffness: 260,
      }),
      withSpring(1, {
        damping: 8,
        stiffness: 220,
      }),
    ));

    store.toggleFavorite(kind, id);
  };

  const label =
    accessibilityLabel ??
    (active
      ? "Remover dos favoritos"
      : "Adicionar aos favoritos");

  return (
    <Pressable
      testID={testID ?? `favorite-${kind}-${id}`}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected: active }}
      hitSlop={6}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.button,
        pressed && styles.pressed,
      ]}
    >
      <AnimatedIcon
        name="heart"
        size={size}
        color={
          active
            ? colors.plum
            : colors.onSurface
        }
        style={animatedStyle}
      />
    </Pressable>
  );
}

const useStyles = makeStyles(() => ({
  button: {
    width: touch.minimum,
    height: touch.minimum,
    alignItems: "center",
    justifyContent: "center",
  },

  pressed: {
    opacity: 0.78,
  },
}));