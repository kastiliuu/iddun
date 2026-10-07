import React, {
  useState,
} from "react";

import {
  Pressable,
} from "react-native";

import * as Haptics from "expo-haptics";

import {
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withSpring,
} from "react-native-reanimated";

import {
  saveGraphTarget,
  type SaveTargetType,
  unsaveGraphTarget,
} from "@/api/graph";

import {
  AnimatedIcon,
} from "@/components/Icon";

import {
  useToast,
} from "@/components/Toast";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import {
  makeStyles,
  touch,
  useTheme,
} from "@/theme";


export type FavoriteKind =
  | "posts"
  | "professionals"
  | "services";


type FavoriteButtonProps = {
  kind: FavoriteKind;
  id: string;
  targetId?: number;
  targetType?: SaveTargetType;
  size?: number;
  testID?: string;
  accessibilityLabel?: string;
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
    Number.isInteger(
      value,
    ) &&
    value > 0
  )
    ? value
    : null;
}


function saveTargetType(
  kind: FavoriteKind,
  explicit?:
    SaveTargetType,
) {
  if (explicit) {
    return explicit;
  }

  if (
    kind ===
    "services"
  ) {
    return "experience";
  }

  if (
    kind ===
    "professionals"
  ) {
    return "professional";
  }

  if (
    kind ===
    "posts"
  ) {
    return "work_post";
  }

  return null;
}


export function FavoriteButton({
  kind,
  id,
  targetId: explicitTargetId,
  targetType,
  size = 22,
  testID,
  accessibilityLabel,
}: FavoriteButtonProps) {
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
    explicitTargetId ??
    numericTargetId(id);

  const graphTargetType =
    saveTargetType(
      kind,
      targetType,
    );

  const serverBacked =
    targetId !== null &&
    graphTargetType !== null;

  const active =
    serverBacked
      ? store.isGraphSaved(
          graphTargetType,
          targetId,
        )
      : store.isFavorite(
          kind,
          id,
        );

  const scale =
    useSharedValue(1);

  const animatedStyle =
    useAnimatedStyle(
      () => ({
        transform: [
          {
            scale:
              scale.get(),
          },
        ],
      }),
    );

  const handlePress =
    async () => {
      if (busy) {
        return;
      }

      Haptics.impactAsync(
        Haptics
          .ImpactFeedbackStyle
          .Medium,
      ).catch(
        () => {},
      );

      scale.set(
        withSequence(
          withSpring(
            1.28,
            {
              damping: 7,
              stiffness: 260,
            },
          ),
          withSpring(
            1,
            {
              damping: 8,
              stiffness: 220,
            },
          ),
        ),
      );

      if (!serverBacked) {
        store.toggleFavorite(
          kind,
          id,
        );
        return;
      }

      const willSave =
        !active;

      const user =
        store.getUser();

      if (!user) {
        toast.show({
          title:
            "Entre para salvar",
          body:
            "Salvos reais ficam vinculados à sua conta IDDUN.",
          icon:
            "bookmark",
        });

        return;
      }

      store.setGraphSaved(
        graphTargetType,
        targetId,
        willSave,
      );

      setBusy(true);

      try {
        if (willSave) {
          await saveGraphTarget(
            graphTargetType,
            targetId,
          );
        } else {
          await unsaveGraphTarget(
            graphTargetType,
            targetId,
          );
        }
      } catch (error) {
        store.setGraphSaved(
          graphTargetType,
          targetId,
          !willSave,
        );

        toast.show({
          title:
            "Não foi possível atualizar seus salvos",
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

  const label =
    accessibilityLabel ??
    (
      active
        ? "Remover dos salvos"
        : "Salvar"
    );

  return (
    <Pressable
      testID={
        testID ??
        `favorite-${kind}-${id}`
      }
      accessibilityRole="button"
      accessibilityLabel={
        label
      }
      accessibilityState={{
        selected:
          active,
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
        styles.button,
        pressed &&
          styles.pressed,
        busy &&
          styles.disabled,
      ]}
    >
      <AnimatedIcon
        name="heart"
        size={size}
        color={
          active
            ? colors.plum
            : colors
                .onSurface
        }
        style={
          animatedStyle
        }
      />
    </Pressable>
  );
}


const useStyles =
  makeStyles(
    () => ({
      button: {
        width:
          touch.minimum,
        height:
          touch.minimum,
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      pressed: {
        opacity: 0.78,
      },

      disabled: {
        opacity: 0.55,
      },
    }),
  );
