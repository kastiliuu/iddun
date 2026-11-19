import React, {
  useEffect,
  useState,
} from "react";

import {
  ActivityIndicator,
  View,
} from "react-native";

import {
  Stack,
} from "expo-router";

import {
  setStatusBarStyle,
} from "expo-status-bar";

import {
  GestureHandlerRootView,
} from "react-native-gesture-handler";

import {
  BottomSheetModalProvider,
} from "@gorhom/bottom-sheet";

import {
  SafeAreaProvider,
} from "react-native-safe-area-context";

import {
  getCurrentUser,
} from "@/api/auth";

import {
  ToastProvider,
} from "@/components/Toast";

import {
  store,
} from "@/store/local";
import { loadThemePreference } from "@/store/themePreference";

import {
  syncBeautyGraph,
} from "@/store/graphSync";

import {
  makeStyles,
  ThemeScope,
  useTheme,
} from "@/theme";

export default function RootLayout() {
  const styles =
    useStyles();

  const { colors } =
    useTheme();

  const [
    ready,
    setReady,
  ] =
    useState(false);

  useEffect(
    () => {
      let mounted =
        true;

      const initialize =
        async () => {
          try {
            // Tema salvo antes da primeira tela, para não piscar.
            await Promise.all([
              store.load(),
              loadThemePreference(),
            ]);

            try {
              const user =
                await getCurrentUser();

              if (!user) {
                store.setUser(null);
              } else {
                try {
                  await syncBeautyGraph();
                } catch {
                  // Mantém escolhas locais para reconciliar depois.
                }
              }
            } catch {
              // Uma falha de rede não apaga os tokens salvos.
              // O app abre como visitante até a próxima verificação.
              store.setUser(null);
            }
          } catch {
            // A experiência básica continua disponível.
            store.setUser(null);
          } finally {
            if (mounted) {
              setReady(true);
            }
          }
        };

      void initialize();

      return () => {
        mounted = false;
      };
    },
    [],
  );

  if (!ready) {
    return (
      <View
        accessible
        accessibilityRole="progressbar"
        accessibilityLabel="Verificando sessão do IDDUN"
        style={[
          styles.loading,
          {
            backgroundColor:
              colors.surface,
          },
        ]}
      >
        <ActivityIndicator
          color={colors.plum}
        />
      </View>
    );
  }

  return (
    <GestureHandlerRootView
      style={styles.root}
    >
      <SafeAreaProvider>
        <BottomSheetModalProvider>
          <ToastProvider>
            {/*
              V1 PR 3 · DS-V1-01-D03: o app inteiro segue a preferência de
              tema (claro padrão, escuro opcional), não só as abas. O
              cabeçalho preto continua fixo em cada tela (D01).
            */}
            <ThemeScope>
              <ThemedStack>
              <Stack.Screen
                name="index"
              />

              <Stack.Screen
                name="onboarding"
              />

              <Stack.Screen
                name="login"
              />

              <Stack.Screen
                name="forgot-password"
              />

              <Stack.Screen
                name="sessions"
              />

              <Stack.Screen
                name="privacy"
              />

              <Stack.Screen
                name="(tabs)"
              />

              <Stack.Screen
                name="notifications"
              />

              <Stack.Screen
                name="create"
              />

              <Stack.Screen
                name="contexts"
              />

              <Stack.Screen
                name="context/professional"
              />

              <Stack.Screen
                name="context/establishment/[id]"
              />

              <Stack.Screen
                name="booking-detail"
              />

              <Stack.Screen
                name="jobs"
              />

              <Stack.Screen
                name="job/[id]"
              />

              <Stack.Screen
                name="job-applications"
              />

              <Stack.Screen
                name="manage-jobs/[id]"
              />

              <Stack.Screen
                name="job-candidates/[establishmentId]/[jobId]"
              />

              <Stack.Screen
                name="team-invitations"
              />

              <Stack.Screen
                name="establishment-team/[id]"
              />

              <Stack.Screen
                name="iddun-now"
              />

              <Stack.Screen
                name="manage-services"
              />

              <Stack.Screen
                name="create-service"
              />

              <Stack.Screen
                name="manage-service/[id]"
              />

              <Stack.Screen
                name="create-post"
              />

              <Stack.Screen
                name="open-slot"
              />

              <Stack.Screen
                name="signup-pro/index"
              />

              <Stack.Screen
                name="professional-onboarding"
              />

              <Stack.Screen
                name="pro-onboarding"
              />

              <Stack.Screen
                name="business-onboarding"
              />

              <Stack.Screen
                name="professional/[id]"
              />

              <Stack.Screen
                name="establishment/[id]"
              />

              <Stack.Screen
                name="service/[id]"
              />

              <Stack.Screen
                name="post/[id]"
              />

              <Stack.Screen
                name="client/[id]"
              />

              <Stack.Screen
                name="booking/[serviceId]"
              />
              </ThemedStack>
            </ThemeScope>
          </ToastProvider>
        </BottomSheetModalProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

function ThemedStack({
  children,
}: {
  children: React.ReactNode;
}) {
  const { colors, scheme } = useTheme();

  // Barra de status legível no fundo do tema; as abas, com cabeçalho
  // preto, voltam a usar texto claro enquanto estão em foco.
  useEffect(() => {
    setStatusBarStyle(scheme === "light" ? "dark" : "light");
  }, [scheme]);

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: {
          backgroundColor: colors.surface,
        },
        animation: "slide_from_right",
      }}
    >
      {children}
    </Stack>
  );
}

const useStyles =
  makeStyles(
    () => ({
      root: {
        flex: 1,
      },

      loading: {
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
      },
    }),
  );