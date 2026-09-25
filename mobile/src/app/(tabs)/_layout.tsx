import React from "react";

import {
  GestureResponderEvent,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Tabs } from "expo-router";
import { BlurView } from "expo-blur";
import * as Haptics from "expo-haptics";

import { Icon } from "@/components/Icon";

import {
  fonts,
  makeStyles,
  radius,
  SPARK,
  useTheme,
} from "@/theme";

type CenterTabButtonProps = {
  accessibilityState?: {
    selected?: boolean;
  };

  accessibilityLabel?: string;

  testID?: string;

  onPress?: (
    event: any,
  ) => void;
};

function CenterTabButton({
  accessibilityState,
  accessibilityLabel,
  testID,
  onPress,
}: CenterTabButtonProps) {
  const styles =
    useStyles();

  const selected =
    accessibilityState?.selected ===
    true;

  const handlePress = (
    event: GestureResponderEvent,
  ) => {
    Haptics.impactAsync(
      Haptics
        .ImpactFeedbackStyle
        .Medium,
    ).catch(() => {});

    onPress?.(event);
  };

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={
        accessibilityLabel ??
        "Criar"
      }
      accessibilityState={{
        selected,
      }}
      onPress={
        handlePress
      }
      hitSlop={6}
      style={({
        pressed,
      }) => [
        styles.centerTabOuter,

        pressed &&
          styles.centerTabPressed,
      ]}
    >
      <View
        style={[
          styles.centerTabButton,

          selected &&
            styles.centerTabButtonActive,
        ]}
      >
        <Text
          accessible={
            false
          }
          style={
            styles.centerSpark
          }
        >
          {SPARK}
        </Text>
      </View>

      <Text
        style={[
          styles.centerLabel,

          selected &&
            styles.centerLabelActive,
        ]}
      >
        Criar
      </Text>
    </Pressable>
  );
}

export default function TabsLayout() {
  const styles =
    useStyles();

  const { colors } =
    useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown:
          false,

        tabBarShowLabel:
          true,

        tabBarActiveTintColor:
          colors.onSurface,

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
                tint="dark"
                style={
                  styles.blur
                }
              />

              <View
                pointerEvents="none"
                style={
                  styles.tabBarOverlay
                }
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
            "Descobrir",

          tabBarAccessibilityLabel:
            "Descobrir",

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
        name="create"
        options={{
          title:
            "Criar",

          tabBarAccessibilityLabel:
            "Criar",

          tabBarButton:
            (props) => (
              <CenterTabButton
                accessibilityState={
                  props.accessibilityState
                }
                accessibilityLabel={
                  props.accessibilityLabel
                }
                testID={
                  props.testID
                }
                onPress={
                  props.onPress as any
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

      centerTabOuter: {
        top: -16,

        minWidth: 66,
        minHeight: 74,

        alignItems:
          "center",

        justifyContent:
          "flex-start",
      },

      centerTabPressed: {
        opacity: 0.82,

        transform: [
          {
            scale: 0.97,
          },
        ],
      },

      centerTabButton: {
        width: 54,
        height: 54,

        borderRadius:
          radius.pill,

        alignItems:
          "center",

        justifyContent:
          "center",

        backgroundColor:
          colors.plum,

        borderWidth: 3,

        borderColor:
          colors.surface,

        shadowColor:
          colors.plum,

        shadowOpacity:
          0.28,

        shadowRadius:
          14,

        shadowOffset: {
          width: 0,
          height: 5,
        },

        elevation: 8,
      },

      centerTabButtonActive: {
        borderColor:
          colors.onBrandTertiary,
      },

      centerSpark: {
        color:
          colors.onBrandPrimary,

        fontFamily:
          fonts.display,

        fontSize: 20,
        lineHeight: 24,
      },

      centerLabel: {
        marginTop: 3,

        color:
          colors.muted,

        fontFamily:
          fonts.sansMedium,

        fontSize: 10,
        lineHeight: 13,
      },

      centerLabelActive: {
        color:
          colors.onSurface,
      },
    }),
  );