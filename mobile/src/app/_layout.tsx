import React, {
  useEffect,
  useState,
} from "react";

import {
  View,
} from "react-native";

import {
  Stack,
} from "expo-router";

import {
  StatusBar,
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
  ToastProvider,
} from "@/components/Toast";

import {
  store,
} from "@/store/local";

import {
  makeStyles,
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
            await store.load();
          } finally {
            if (
              mounted
            ) {
              setReady(
                true,
              );
            }
          }
        };

      initialize();

      return () => {
        mounted =
          false;
      };
    },
    [],
  );

  if (!ready) {
    return (
      <View
        style={[
          styles.loading,
          {
            backgroundColor:
              colors.surface,
          },
        ]}
      />
    );
  }

  return (
    <GestureHandlerRootView
      style={
        styles.root
      }
    >
      <SafeAreaProvider>
        <BottomSheetModalProvider>
          <ToastProvider>
            <StatusBar
              style="light"
            />

            <Stack
              screenOptions={{
                headerShown:
                  false,

                contentStyle: {
                  backgroundColor:
                    colors.surface,
                },

                animation:
                  "slide_from_right",
              }}
            >
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
                name="(tabs)"
              />

              <Stack.Screen
                name="notifications"
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
                name="open-slot"
              />

              <Stack.Screen
                name="signup-pro/index"
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
                name="booking/[serviceId]"
              />
            </Stack>
          </ToastProvider>
        </BottomSheetModalProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
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
      },
    }),
  );