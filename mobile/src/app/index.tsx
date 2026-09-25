import React, { useEffect } from "react";
import {
  ActivityIndicator,
  View,
} from "react-native";
import { router } from "expo-router";

import {
  getOnboarded,
} from "@/store/local";

import {
  makeStyles,
  SPARK,
  useTheme,
} from "@/theme";

export default function IndexScreen() {
  const styles = useStyles();
  const { colors } = useTheme();

  useEffect(() => {
    let active = true;

    const resolveInitialRoute =
      async () => {
        try {
          const onboarded =
            await getOnboarded();

          if (!active) {
            return;
          }

          router.replace(
            onboarded
              ? "/(tabs)"
              : "/onboarding",
          );
        } catch {
          if (!active) {
            return;
          }

          /**
           * Em caso de qualquer problema local,
           * começamos pelo onboarding.
           */
          router.replace(
            "/onboarding",
          );
        }
      };

    void resolveInitialRoute();

    return () => {
      active = false;
    };
  }, []);

  return (
    <View style={styles.container}>
      <View
        accessible
        accessibilityRole="text"
        accessibilityLabel="Carregando IDDUN"
        style={styles.brandMark}
      >
        <View style={styles.sparkWrap}>
          <ActivityIndicator
            size="small"
            color={colors.plum}
          />
        </View>
      </View>
    </View>
  );
}

const useStyles = makeStyles(
  (colors) => ({
    container: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor:
        colors.surface,
    },

    brandMark: {
      alignItems: "center",
      justifyContent: "center",
    },

    sparkWrap: {
      width: 46,
      height: 46,
      alignItems: "center",
      justifyContent: "center",
    },
  }),
);