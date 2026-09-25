import React from "react";
import { Pressable, Text } from "react-native";
import * as Haptics from "expo-haptics";
import { useRouter } from "expo-router";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import { useToast } from "@/components/Toast";

type FollowButtonProps = {
  id: string;
  authorName?: string;
  testID?: string;
};

export function FollowButton({
  id,
  authorName,
  testID,
}: FollowButtonProps) {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const following = store.isFollowing(id);

  const handlePress = () => {
    Haptics.impactAsync(
      Haptics.ImpactFeedbackStyle.Light,
    ).catch(() => {});

    const willFollow = !following;

    store.toggleFollow(id, {
      authorName:
        authorName?.split(" ")[0],

      onAlert: (notification) => {
        toast.show({
          title: notification.title,
          body: notification.timeLabel
            ? `${notification.timeLabel} · ${notification.body}`
            : notification.body,
          icon: "clock",
          onPress: () => {
            router.push("/notifications");
          },
        });
      },
    });

    if (willFollow) {
      toast.show({
        title: authorName
          ? `Você agora segue ${authorName.split(" ")[0]}`
          : "Perfil seguido",

        body:
          "Vamos avisar quando aparecer um novo horário disponível.",

        icon: "bell",
      });
    }
  };

  return (
    <Pressable
      testID={
        testID ??
        `follow-${id}`
      }
      accessibilityRole="button"
      accessibilityLabel={
        following
          ? `Deixar de seguir ${authorName ?? "perfil"}`
          : `Seguir ${authorName ?? "perfil"}`
      }
      accessibilityState={{
        selected: following,
      }}
      hitSlop={6}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.base,

        following
          ? styles.following
          : styles.follow,

        pressed && styles.pressed,
      ]}
    >
      <Text
        style={[
          styles.text,
          {
            color: following
              ? colors.onSurface
              : colors.onBrandPrimary,
          },
        ]}
      >
        {following
          ? "Seguindo"
          : "Seguir"}
      </Text>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  base: {
    minWidth: 96,
    minHeight: touch.minimum,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },

  follow: {
    backgroundColor: colors.plum,
    borderWidth: 1,
    borderColor: colors.plum,
  },

  following: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.border,
  },

  pressed: {
    opacity: 0.82,
  },

  text: {
    fontFamily: fonts.sansMedium,
    fontSize: 13,
    letterSpacing: 0.2,
  },
}));