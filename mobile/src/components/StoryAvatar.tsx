import React from "react";
import { Pressable, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";

import { Avatar } from "@/components/Avatar";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";

type StoryAvatarProps = {
  id: string;
  name: string;
  uri?: string | null;
  seen?: boolean;
  routeType?: "professional" | "establishment";
  onPress?: () => void;
};

export function StoryAvatar({
  id,
  name,
  uri,
  seen = false,
  routeType = "professional",
  onPress,
}: StoryAvatarProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const firstName =
    name.trim().split(/\s+/)[0] || name;

  const handlePress = () => {
    if (onPress) {
      onPress();
      return;
    }

    router.push(
      routeType === "establishment"
        ? `/establishment/${id}`
        : `/professional/${id}`,
    );
  };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Abrir perfil de ${name}`}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.container,
        pressed && styles.pressed,
      ]}
    >
      {seen ? (
        <View style={styles.seenRing}>
          <Avatar
            name={name}
            uri={uri}
            size={58}
          />
        </View>
      ) : (
        <LinearGradient
          colors={[
            colors.plum,
            colors.onBrandTertiary,
            colors.deepViolet,
          ]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.activeRing}
        >
          <View style={styles.innerRing}>
            <Avatar
              name={name}
              uri={uri}
              size={54}
            />
          </View>
        </LinearGradient>
      )}

      <Text
        style={[
          styles.name,
          {
            color: seen
              ? colors.muted
              : colors.onSurface,
          },
        ]}
        numberOfLines={1}
      >
        {firstName}
      </Text>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    width: 72,
    alignItems: "center",
  },

  pressed: {
    opacity: 0.8,
  },

  activeRing: {
    width: 64,
    height: 64,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },

  innerRing: {
    width: 60,
    height: 60,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
  },

  seenRing: {
    width: 64,
    height: 64,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surfaceTertiary,
    borderWidth: 1,
    borderColor: colors.border,
  },

  name: {
    width: "100%",
    marginTop: spacing.sm,
    fontFamily: fonts.sans,
    fontSize: 11,
    lineHeight: 14,
    textAlign: "center",
  },
}));