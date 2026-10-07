import React, {
  useState,
} from "react";

import {
  Pressable,
  Text,
} from "react-native";

import * as Haptics from "expo-haptics";

import {
  followGraphTarget,
  type FollowTargetType,
  unfollowGraphTarget,
} from "@/api/graph";

import {
  useToast,
} from "@/components/Toast";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";


type FollowButtonProps = {
  id: string;
  targetType?: FollowTargetType;
  authorName?: string;
  testID?: string;
};


function numericTargetId(
  id: string,
) {
  if (
    !/^\d+$/.test(id)
  ) {
    return null;
  }

  const value =
    Number(id);

  return (
    Number.isInteger(value) &&
    value > 0
  )
    ? value
    : null;
}


export function FollowButton({
  id,
  targetType = "professional",
  authorName,
  testID,
}: FollowButtonProps) {
  useStoreVersion();

  const styles =
    useStyles();

  const { colors } =
    useTheme();

  const toast =
    useToast();

  const [
    busy,
    setBusy,
  ] =
    useState(false);

  const targetId =
    numericTargetId(id);

  const serverBacked =
    targetId !== null;

  const following =
    serverBacked
      ? store.isGraphFollowing(
          targetType,
          targetId,
        )
      : store.isFollowing(
          id,
        );

  const handlePress =
    async () => {
      if (busy) {
        return;
      }

      Haptics.impactAsync(
        Haptics
          .ImpactFeedbackStyle
          .Light,
      ).catch(
        () => {},
      );

      const willFollow =
        !following;

      if (!serverBacked) {
        store.toggleFollow(
          id,
        );

        if (willFollow) {
          toast.show({
            title:
              authorName
                ? (
                  "Você agora segue "
                  + authorName
                    .split(
                      " ",
                    )[0]
                )
                : "Perfil seguido",
            body:
              "Essa escolha está salva neste aparelho enquanto este perfil ainda usa dados de demonstração.",
            icon:
              "bell",
          });
        }

        return;
      }

      store.setGraphFollowing(
        targetType,
        targetId,
        willFollow,
      );

      const user =
        store.getUser();

      if (!user) {
        if (willFollow) {
          toast.show({
            title:
              "Perfil seguido",
            body:
              "Entre na sua conta depois para levar essa escolha para outros aparelhos.",
            icon:
              "bell",
          });
        }

        return;
      }

      setBusy(true);

      try {
        if (willFollow) {
          await followGraphTarget(
            targetType,
            targetId,
          );
        } else {
          await unfollowGraphTarget(
            targetType,
            targetId,
          );
        }

        if (willFollow) {
          toast.show({
            title:
              authorName
                ? (
                  "Você agora segue "
                  + authorName
                    .split(
                      " ",
                    )[0]
                )
                : "Perfil seguido",
            body:
              "Essa escolha agora faz parte da sua conta IDDUN.",
            icon:
              "bell",
          });
        }
      } catch (error) {
        store.setGraphFollowing(
          targetType,
          targetId,
          !willFollow,
        );

        toast.show({
          title:
            "Não foi possível atualizar",
          body:
            error instanceof Error
              ? error.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setBusy(false);
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
          ? (
            "Deixar de seguir "
            + (
              authorName ??
              "perfil"
            )
          )
          : (
            "Seguir "
            + (
              authorName ??
              "perfil"
            )
          )
      }
      accessibilityState={{
        selected:
          following,
        disabled:
          busy,
      }}
      disabled={busy}
      hitSlop={6}
      onPress={() =>
        void handlePress()
      }
      style={({
        pressed,
      }) => [
        styles.base,

        following
          ? styles.following
          : styles.follow,

        pressed &&
          styles.pressed,

        busy &&
          styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.text,
          {
            color:
              following
                ? colors
                    .onSurface
                : colors
                    .onBrandPrimary,
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


const useStyles =
  makeStyles(
    (colors) => ({
      base: {
        minWidth: 96,
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.lg,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      follow: {
        backgroundColor:
          colors.plum,
        borderWidth: 1,
        borderColor:
          colors.plum,
      },

      following: {
        backgroundColor:
          "transparent",
        borderWidth: 1,
        borderColor:
          colors.border,
      },

      pressed: {
        opacity: 0.82,
      },

      disabled: {
        opacity: 0.55,
      },

      text: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 13,
        letterSpacing: 0.2,
      },
    }),
  );
