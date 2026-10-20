import { useMemo } from "react";
import { StyleSheet } from "react-native";

export type ColorScheme = "dark" | "light";

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


/**
 * Design System 2.0 — Editorial Híbrido.
 * Semantic palettes are additive: legacy `colors`, `theme`, `useTheme`
 * and `makeStyles` remain dark for existing screens.
 * A later PR will add persisted preference and migrate consumers safely.
 */
export const semanticPalettes = {
  dark: {
    canvas: "#0B0B0F",
    surface: "#16161C",
    elevated: "#1F1F26",
    inverse: "#F7F6F4",
    textPrimary: "#F7F6F4",
    textSecondary: "#DADDE1",
    textMuted: "#A3A3AF",
    textInverse: "#0B0B0F",
    border: "rgba(255,255,255,0.14)",
    borderSubtle: "rgba(255,255,255,0.08)",
    action: "#6B2EFF",
    actionPressed: "#7B46FF",
    onAction: "#FFFFFF",
    focus: "#B199FF",
    link: "#B199FF",
  },
  light: {
    canvas: "#F7F6F4",
    surface: "#FFFFFF",
    elevated: "#FFFFFF",
    inverse: "#0B0B0F",
    textPrimary: "#0B0B0F",
    textSecondary: "#51525C",
    textMuted: "#62636E",
    textInverse: "#FFFFFF",
    border: "rgba(11,11,15,0.16)",
    borderSubtle: "rgba(11,11,15,0.08)",
    action: "#6B2EFF",
    actionPressed: "#5920DF",
    onAction: "#FFFFFF",
    focus: "#5920DF",
    link: "#5420CC",
  },
} as const;

export const designScale = {
  typography: {
    caption: 12,
    captionLarge: 13,
    secondary: 14,
    body: 16,
    headingSmall: 20,
    headingMedium: 24,
  },
  spacing: {
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    6: 24,
    8: 32,
    12: 48,
  },
  radius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
  },
  touchMinimum: 44,
} as const;

export function getSemanticPalette(scheme: ColorScheme) {
  return semanticPalettes[scheme];
}

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