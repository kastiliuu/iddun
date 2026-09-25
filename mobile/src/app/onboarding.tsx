import React, {
  useRef,
  useState,
} from "react";
import {
  Dimensions,
  FlatList,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import * as Haptics from "expo-haptics";

import { Button } from "@/components/Button";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  useTheme,
} from "@/theme";

import {
  markOnboarded,
} from "@/store/local";

const { width } =
  Dimensions.get("window");

type OnboardingSlide = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  image: string;
};

const slides: OnboardingSlide[] = [
  {
    id: "discovery",

    eyebrow: "DESCUBRA",

    title:
      "Encontre beleza que combina com você.",

    description:
      "Explore profissionais, estilos, serviços e lugares que transformam cuidado em experiência.",

    image:
      "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=90",
  },

  {
    id: "connection",

    eyebrow: "CONECTE-SE",

    title:
      "Siga quem inspira o seu estilo.",

    description:
      "Acompanhe profissionais e estabelecimentos, salve favoritos e descubra novidades no seu próprio feed.",

    image:
      "https://images.unsplash.com/photo-1604654894610-df63bc536371?auto=format&fit=crop&w=1200&q=90",
  },

  {
    id: "experience",

    eyebrow: "VIVA A EXPERIÊNCIA",

    title:
      "Quando surgir o momento certo, agende.",

    description:
      "Do conteúdo ao horário disponível. Tudo conectado para transformar descoberta em experiência.",

    image:
      "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=1200&q=90",
  },
];

export default function OnboardingScreen() {
  const styles = useStyles();
  const { colors } = useTheme();

  const listRef =
    useRef<FlatList<OnboardingSlide>>(
      null,
    );

  const [currentIndex, setCurrentIndex] =
    useState(0);

  const isLast =
    currentIndex ===
    slides.length - 1;

  const finishOnboarding =
    async () => {
      await markOnboarded();

      router.replace("/(tabs)");
    };

  const handleContinue =
    async () => {
      Haptics.impactAsync(
        Haptics
          .ImpactFeedbackStyle
          .Light,
      ).catch(() => {});

      if (isLast) {
        await finishOnboarding();
        return;
      }

      const nextIndex =
        currentIndex + 1;

      listRef.current?.scrollToIndex({
        index: nextIndex,
        animated: true,
      });

      setCurrentIndex(
        nextIndex,
      );
    };

  const handleVisitor =
    async () => {
      Haptics.impactAsync(
        Haptics
          .ImpactFeedbackStyle
          .Light,
      ).catch(() => {});

      await finishOnboarding();
    };

  const handleScrollEnd = (
    event: NativeSyntheticEvent<
      NativeScrollEvent
    >,
  ) => {
    const offsetX =
      event.nativeEvent
        .contentOffset.x;

    const index =
      Math.round(
        offsetX / width,
      );

    setCurrentIndex(
      Math.max(
        0,
        Math.min(
          slides.length - 1,
          index,
        ),
      ),
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        ref={listRef}
        data={slides}
        keyExtractor={(item) => item.id}
        horizontal
        pagingEnabled
        bounces={false}
        showsHorizontalScrollIndicator={
          false
        }
        onMomentumScrollEnd={
          handleScrollEnd
        }
        getItemLayout={(
          _,
          index,
        ) => ({
          length: width,
          offset:
            width * index,
          index,
        })}
        renderItem={({
          item,
        }) => (
          <View
            style={[
              styles.slide,
              {
                width,
              },
            ]}
          >
            <Image
              source={{
                uri: item.image,
              }}
              style={
                StyleSheet
                  .absoluteFill
              }
              contentFit="cover"
              transition={250}
              accessibilityLabel={
                item.title
              }
            />

            <LinearGradient
              pointerEvents="none"
              colors={[
                "rgba(11,11,15,0.12)",
                colors.overlayInkSoft,
                colors.overlayInkStrong,
                colors.overlayInkHeavy,
              ]}
              locations={[
                0,
                0.42,
                0.72,
                1,
              ]}
              style={
                StyleSheet
                  .absoluteFill
              }
            />

            <View
              style={
                styles.topBrand
              }
            >
              <Text
                style={
                  styles.brand
                }
              >
                IDDUN
              </Text>

              <Text
                accessible={false}
                style={
                  styles.brandSpark
                }
              >
                {SPARK}
              </Text>
            </View>

            <View
              style={
                styles.content
              }
            >
              <View
                style={
                  styles.eyebrowRow
                }
              >
                <Text
                  accessible={
                    false
                  }
                  style={
                    styles.spark
                  }
                >
                  {SPARK}
                </Text>

                <Text
                  style={
                    styles.eyebrow
                  }
                >
                  {item.eyebrow}
                </Text>
              </View>

              <Text
                style={
                  styles.title
                }
              >
                {item.title}
              </Text>

              <Text
                style={
                  styles.description
                }
              >
                {
                  item.description
                }
              </Text>
            </View>
          </View>
        )}
      />

      <View
        style={
          styles.bottomArea
        }
      >
        <View
          style={
            styles.pagination
          }
        >
          {slides.map(
            (_, index) => {
              const active =
                index ===
                currentIndex;

              return (
                <View
                  key={index}
                  style={[
                    styles.dot,
                    active &&
                      styles.dotActive,
                  ]}
                />
              );
            },
          )}
        </View>

        <Button
          title={
            isLast
              ? "Começar a descobrir"
              : "Continuar"
          }
          onPress={
            handleContinue
          }
          fullWidth
        />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Continuar como visitante"
          onPress={
            handleVisitor
          }
          style={({ pressed }) => [
            styles.visitorButton,
            pressed &&
              styles.visitorPressed,
          ]}
        >
          <Text
            style={
              styles.visitorText
            }
          >
            Continuar como visitante
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const useStyles = makeStyles(
  (colors) => ({
    container: {
      flex: 1,
      backgroundColor:
        colors.surface,
    },

    slide: {
      flex: 1,
      position: "relative",
      backgroundColor:
        colors.surface,
    },

    topBrand: {
      position:
        "absolute",

      top: 64,
      left: spacing.xl,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,
    },

    brand: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 23,
      lineHeight: 28,

      letterSpacing: 2.8,
    },

    brandSpark: {
      color:
        colors.plum,

      fontFamily:
        fonts.display,

      fontSize: 14,
      lineHeight: 18,
    },

    content: {
      position:
        "absolute",

      left: spacing.xl,
      right: spacing.xl,

      bottom: 195,
    },

    eyebrowRow: {
      flexDirection:
        "row",

      alignItems:
        "center",

      gap: spacing.sm,

      marginBottom:
        spacing.md,
    },

    spark: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 13,
      lineHeight: 17,
    },

    eyebrow: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 11,
      lineHeight: 15,

      letterSpacing: 1.6,
    },

    title: {
      maxWidth: 340,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 38,
      lineHeight: 43,

      letterSpacing: -0.6,
    },

    description: {
      maxWidth: 330,

      marginTop:
        spacing.lg,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 14,
      lineHeight: 21,
    },

    bottomArea: {
      position:
        "absolute",

      left: 0,
      right: 0,
      bottom: 0,

      paddingHorizontal:
        spacing.xl,

      paddingTop:
        spacing.lg,

      paddingBottom: 28,

      backgroundColor:
        colors.overlayInkHeavy,

      borderTopWidth: 1,
      borderTopColor:
        colors.glassBorder,
    },

    pagination: {
      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "center",

      gap: spacing.sm,

      marginBottom:
        spacing.lg,
    },

    dot: {
      width: 6,
      height: 6,

      borderRadius:
        radius.pill,

      backgroundColor:
        colors.surfaceTertiary,
    },

    dotActive: {
      width: 24,

      backgroundColor:
        colors.plum,
    },

    visitorButton: {
      minHeight: 44,

      marginTop:
        spacing.sm,

      alignItems:
        "center",

      justifyContent:
        "center",
    },

    visitorPressed: {
      opacity: 0.65,
    },

    visitorText: {
      color:
        colors.muted,

      fontFamily:
        fonts.sansMedium,

      fontSize: 12,
      lineHeight: 16,
    },
  }),
);