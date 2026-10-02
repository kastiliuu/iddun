import React, { useMemo, useState } from "react";
import { Text, View } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";

import {
  fonts,
  makeStyles,
  useTheme,
} from "@/theme";

type AvatarRing = "none" | "plum";

type AvatarProps = {
  name: string;
  uri?: string | null;
  size?: number;
  ring?: AvatarRing;
  accessibilityLabel?: string;
};

function getInitials(name: string) {
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) return "?";

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export function Avatar({
  name,
  uri,
  size = 44,
  ring = "none",
  accessibilityLabel,
}: AvatarProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [failedUri, setFailedUri] =
    useState<string | null>(null);

  const initials = useMemo(() => getInitials(name), [name]);

  const imageSize = ring === "plum" ? size - 4 : size;

  const avatarContent = uri && failedUri !== uri ? (
    <Image
      source={{ uri }}
      style={{
        width: imageSize,
        height: imageSize,
        borderRadius: imageSize / 2,
        backgroundColor: colors.surfaceTertiary,
      }}
      contentFit="cover"
      transition={180}
      onError={() => setFailedUri(uri)}
      accessibilityLabel={accessibilityLabel ?? `Foto de ${name}`}
    />
  ) : (
    <LinearGradient
      colors={[colors.plum, colors.deepViolet]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={[
        styles.fallback,
        {
          width: imageSize,
          height: imageSize,
          borderRadius: imageSize / 2,
        },
      ]}
      accessibilityLabel={accessibilityLabel ?? `Avatar de ${name}`}
    >
      <Text
        style={[
          styles.initials,
          {
            fontSize: Math.max(11, imageSize * 0.32),
            lineHeight: Math.max(14, imageSize * 0.38),
          },
        ]}
      >
        {initials}
      </Text>
    </LinearGradient>
  );

  if (ring === "plum") {
    return (
      <LinearGradient
        colors={[
          colors.plum,
          colors.onBrandTertiary,
          colors.plum,
        ]}
        style={[
          styles.ring,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
          },
        ]}
      >
        <View
          style={[
            styles.ringInner,
            {
              width: size - 3,
              height: size - 3,
              borderRadius: (size - 3) / 2,
              backgroundColor: colors.surface,
            },
          ]}
        >
          {avatarContent}
        </View>
      </LinearGradient>
    );
  }

  return avatarContent;
}

const useStyles = makeStyles((colors) => ({
  ring: {
    alignItems: "center",
    justifyContent: "center",
  },

  ringInner: {
    alignItems: "center",
    justifyContent: "center",
  },

  fallback: {
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },

  initials: {
    color: colors.white,
    fontFamily: fonts.sansSemiBold,
    textAlign: "center",
    letterSpacing: 0.4,
  },
}));