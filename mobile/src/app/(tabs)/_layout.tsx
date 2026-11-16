import React from "react";

import {
  Platform,
  StyleSheet,
  View,
} from "react-native";

import { Tabs } from "expo-router";
import { BlurView } from "expo-blur";

import { Icon } from "@/components/Icon";

import {
  fonts,
  makeStyles,
  ThemeScope,
  useTheme,
} from "@/theme";


/**
 * DS-V1-01-D03: as cinco abas do Cliente são a primeira jornada do app
 * que segue a preferência de tema (claro por padrão, escuro opcional).
 * As telas abertas a partir delas continuam escuras até serem conferidas.
 */
export default function TabsLayout() {
  return (
    <ThemeScope>
      <ClientTabs />
    </ThemeScope>
  );
}


function ClientTabs() {
  const styles =
    useStyles();

  const { colors, scheme } =
    useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown:
          false,

        tabBarShowLabel:
          true,

        tabBarActiveTintColor:
          scheme === "light"
            ? colors.plum
            : colors.onSurface,

        tabBarInactiveTintColor:
          colors.muted,

        tabBarLabelStyle: {
          fontFamily:
            fonts.sansMedium,

          fontSize: 10,

          lineHeight: 13,

          marginTop: 2,
        },

        tabBarStyle: {
          position:
            "absolute",

          left: 0,
          right: 0,
          bottom: 0,

          height:
            Platform.OS ===
            "ios"
              ? 86
              : 72,

          paddingTop: 7,

          paddingBottom:
            Platform.OS ===
            "ios"
              ? 22
              : 10,

          backgroundColor:
            "transparent",

          borderTopWidth: 0,

          elevation: 0,
        },

        tabBarBackground:
          () => (
            <View
              style={
                styles.tabBarBackground
              }
            >
              <BlurView
                intensity={
                  82
                }
                tint={scheme}
                style={
                  styles.blur
                }
              />

              <View
                pointerEvents="none"
                style={[
                  styles.tabBarOverlay,
                  scheme === "light" &&
                    styles.tabBarOverlayLight,
                ]}
              />
            </View>
          ),
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title:
            "Início",

          tabBarAccessibilityLabel:
            "Início",

          tabBarIcon: ({
            color,
            size,
            focused,
          }) => (
            <Icon
              name="home"
              size={
                focused
                  ? size + 1
                  : size
              }
              color={
                color
              }
            />
          ),
        }}
      />

      <Tabs.Screen
        name="discover"
        options={{
          title:
            "Explorar",

          tabBarAccessibilityLabel:
            "Explorar",

          tabBarIcon: ({
            color,
            size,
            focused,
          }) => (
            <Icon
              name="search"
              size={
                focused
                  ? size + 1
                  : size
              }
              color={
                color
              }
            />
          ),
        }}
      />

      <Tabs.Screen
        name="bookings"
        options={{
          title:
            "Reservas",

          tabBarAccessibilityLabel:
            "Reservas",

          tabBarIcon: ({
            color,
            size,
            focused,
          }) => (
            <Icon
              name="calendar"
              size={
                focused
                  ? size + 1
                  : size
              }
              color={
                color
              }
            />
          ),
        }}
      />

      <Tabs.Screen
        name="favorites"
        options={{
          title:
            "Favoritos",

          tabBarAccessibilityLabel:
            "Favoritos",

          tabBarIcon: ({
            color,
            size,
            focused,
          }) => (
            <Icon
              name="heart"
              size={
                focused
                  ? size + 1
                  : size
              }
              color={
                color
              }
            />
          ),
        }}
      />

      <Tabs.Screen
        name="profile"
        options={{
          title:
            "Perfil",

          tabBarAccessibilityLabel:
            "Perfil",

          tabBarIcon: ({
            color,
            size,
            focused,
          }) => (
            <Icon
              name="user"
              size={
                focused
                  ? size + 1
                  : size
              }
              color={
                color
              }
            />
          ),
        }}
      />
    </Tabs>
  );
}

const useStyles =
  makeStyles(
    (colors) => ({
      tabBarBackground: {
        ...StyleSheet.absoluteFill,

        overflow:
          "hidden",

        borderTopWidth: 1,

        borderTopColor:
          colors.glassBorder,
      },

      blur: {
        ...StyleSheet.absoluteFill,
      },

      tabBarOverlay: {
        ...StyleSheet.absoluteFill,

        backgroundColor:
          colors.overlayInkStrong,
      },

      // Claro: a barra é a própria superfície, não uma camada sobre foto.
      tabBarOverlayLight: {
        backgroundColor:
          colors.surfaceSecondary,
        opacity: 0.94,
      },
    }),
  );