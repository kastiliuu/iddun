import { useMemo } from "react";
import { StyleSheet } from "react-native";

export type ColorScheme = "dark";

export const colors = {
  surface: "#0B0B0F",
  onSurface: "#FFFFFF",

  surfaceSecondary: "#16161C",
  onSurfaceSecondary: "#DADDE1",

  surfaceTertiary: "#2A2A33",
  onSurfaceTertiary: "#DADDE1",

  surfaceInverse: "#F7F6F4",
  onSurfaceInverse: "#0B0B0F",

  muted: "#8A8A94",

  brand: "#6B2EFF",
  onBrand: "#FFFFFF",

  brandPrimary: "#6B2EFF",
  onBrandPrimary: "#FFFFFF",

  brandSecondary: "#1A0F2E",
  onBrandSecondary: "#FFFFFF",

  brandTertiary: "#22143A",
  onBrandTertiary: "#B199FF",

  success: "#22C55E",
  onSuccess: "#0B0B0F",

  warning: "#F5A623",
  onWarning: "#0B0B0F",

  error: "#EF4444",
  onError: "#FFFFFF",

  info: "#6B2EFF",
  onInfo: "#FFFFFF",

  border: "#2A2A33",
  borderStrong: "#6B2EFF",
  divider: "#1F1F26",

  ink: "#0B0B0F",
  graphite: "#2A2A33",
  mist: "#DADDE1",
  plum: "#6B2EFF",
  deepViolet: "#1A0F2E",
  white: "#FFFFFF",
  offWhite: "#F7F6F4",

  plumSoft: "rgba(107,46,255,0.14)",
  plumSoftStrong: "rgba(107,46,255,0.22)",

  glassSoft: "rgba(255,255,255,0.06)",
  glassBorder: "rgba(255,255,255,0.10)",
  glassBorderStrong: "rgba(255,255,255,0.14)",

  overlayInkSoft: "rgba(11,11,15,0.55)",
  overlayInk: "rgba(11,11,15,0.72)",
  overlayInkStrong: "rgba(11,11,15,0.95)",
  overlayInkHeavy: "rgba(11,11,15,0.98)",

  overlayViolet: "rgba(26,15,46,0.85)",
};

export type ThemeColors = typeof colors;

export const fonts = {
  display: "PlayfairDisplay",
  displayItalic: "PlayfairDisplay-Italic",

  sans: "Inter",
  sansMedium: "Inter-Medium",
  sansSemiBold: "Inter-SemiBold",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
};

export const radius = {
  sm: 8,
  md: 16,
  lg: 24,
  pill: 999,
};

export const typography = {
  caption: 11,
  small: 12,
  bodySmall: 13,
  body: 14,
  bodyLarge: 16,
  titleSmall: 20,
  title: 24,
  editorial: 32,
  hero: 40,
};

export const touch = {
  minimum: 44,
};

export const SPARK = "✦";

export const theme = {
  colors,
  fonts,
  spacing,
  radius,
  typography,
  touch,
};

export function useTheme() {
  return {
    colors,
    fonts,
    spacing,
    radius,
    typography,
    touch,
    scheme: "dark" as const,
  };
}

export function makeStyles<
  T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>,
>(factory: (themeColors: ThemeColors) => T) {
  return function useStyles() {
    return useMemo(
      () => StyleSheet.create(factory(colors)),
      [],
    );
  };
}