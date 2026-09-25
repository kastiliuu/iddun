import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Pressable,
  Text,
  View,
} from "react-native";
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { LinearGradient } from "expo-linear-gradient";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  useTheme,
} from "@/theme";

import {
  Icon,
  IconName,
} from "@/components/Icon";

type ToastPayload = {
  title: string;
  body?: string;
  icon?: IconName;
  onPress?: () => void;
  duration?: number;
};

type ToastContextValue = {
  show: (payload: ToastPayload) => void;
  hide: () => void;
};

const ToastContext =
  createContext<ToastContextValue>({
    show: () => {},
    hide: () => {},
  });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  const [payload, setPayload] =
    useState<ToastPayload | null>(null);

  const translateY = useSharedValue(-140);
  const opacity = useSharedValue(0);

  const timerRef =
    useRef<ReturnType<typeof setTimeout> | null>(
      null,
    );

  const clearTimer = useCallback(() => {
    if (!timerRef.current) return;

    clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const removePayload = useCallback(() => {
    setPayload(null);
  }, []);

  const hide = useCallback(() => {
    clearTimer();

    translateY.value = withTiming(
      -140,
      {
        duration: 220,
      },
    );

    opacity.value = withTiming(
      0,
      {
        duration: 180,
      },
      (finished) => {
        if (finished) {
          runOnJS(removePayload)();
        }
      },
    );
  }, [
    clearTimer,
    opacity,
    removePayload,
    translateY,
  ]);

  const show = useCallback(
    (nextPayload: ToastPayload) => {
      clearTimer();

      setPayload(nextPayload);

      /**
       * Começamos um pouco acima da área segura.
       */
      translateY.value =
        -(insets.top + 100);

      opacity.value = 0;

      translateY.value = withTiming(
        insets.top + spacing.md,
        {
          duration: 260,
        },
      );

      opacity.value = withTiming(
        1,
        {
          duration: 180,
        },
      );

      timerRef.current = setTimeout(
        () => {
          hide();
        },
        nextPayload.duration ?? 3600,
      );
    },
    [
      clearTimer,
      hide,
      insets.top,
      opacity,
      translateY,
    ],
  );

  useEffect(() => {
    return () => {
      clearTimer();
    };
  }, [clearTimer]);

  const animatedStyle =
    useAnimatedStyle(() => ({
      opacity: opacity.value,
      transform: [
        {
          translateY:
            translateY.value,
        },
      ],
    }));

  const contextValue = useMemo(
    () => ({
      show,
      hide,
    }),
    [show, hide],
  );

  return (
    <ToastContext.Provider
      value={contextValue}
    >
      {children}

      {payload ? (
        <Animated.View
          pointerEvents="box-none"
          style={[
            styles.wrapper,
            animatedStyle,
          ]}
        >
          <Pressable
            testID="toast-body"
            accessibilityRole={
              payload.onPress
                ? "button"
                : undefined
            }
            accessibilityLabel={
              payload.body
                ? `${payload.title}. ${payload.body}`
                : payload.title
            }
            onPress={() => {
              if (!payload.onPress) {
                return;
              }

              payload.onPress();
              hide();
            }}
            style={({ pressed }) => [
              styles.toast,
              pressed &&
                payload.onPress &&
                styles.pressed,
            ]}
          >
            <LinearGradient
              colors={[
                colors.plum,
                colors.deepViolet,
              ]}
              start={{
                x: 0,
                y: 0,
              }}
              end={{
                x: 1,
                y: 1,
              }}
              style={styles.iconWrap}
            >
              <Icon
                name={
                  payload.icon ??
                  "bell"
                }
                size={16}
                color={
                  colors.onBrandPrimary
                }
              />
            </LinearGradient>

            <View style={styles.content}>
              <Text
                style={styles.title}
                numberOfLines={1}
              >
                {SPARK}{" "}
                {payload.title}
              </Text>

              {payload.body ? (
                <Text
                  style={styles.body}
                  numberOfLines={2}
                >
                  {payload.body}
                </Text>
              ) : null}
            </View>

            {payload.onPress ? (
              <Icon
                name="chevron-right"
                size={16}
                color={
                  colors.onSurfaceSecondary
                }
              />
            ) : null}
          </Pressable>
        </Animated.View>
      ) : null}
    </ToastContext.Provider>
  );
}

const useStyles = makeStyles(
  (colors) => ({
    wrapper: {
      position: "absolute",
      top: 0,
      left: spacing.lg,
      right: spacing.lg,
      zIndex: 9999,
      elevation: 20,
    },

    toast: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.md,
      padding: spacing.md,
      borderRadius: radius.md,

      backgroundColor:
        colors.overlayInkStrong,

      borderWidth: 1,
      borderColor:
        colors.brandTertiary,
    },

    pressed: {
      opacity: 0.9,
    },

    iconWrap: {
      width: 36,
      height: 36,
      borderRadius: 12,
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    },

    content: {
      flex: 1,
    },

    title: {
      color: colors.onSurface,
      fontFamily:
        fonts.sansMedium,
      fontSize: 13,
      lineHeight: 17,
      letterSpacing: 0.2,
    },

    body: {
      color:
        colors.onSurfaceSecondary,
      fontFamily: fonts.sans,
      fontSize: 12,
      lineHeight: 17,
      marginTop: 2,
    },
  }),
);