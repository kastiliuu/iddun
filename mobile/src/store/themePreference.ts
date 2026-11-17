import AsyncStorage from "@react-native-async-storage/async-storage";

import {
  DEFAULT_SCHEME,
  setPreferredScheme,
  type ColorScheme,
} from "@/theme";

/**
 * Preferência de tema gravada no aparelho (FE-DEC-002, D-VIS-02): claro
 * por padrão, escuro opcional. É uma escolha de aparência, sem dado
 * pessoal; fica fora da conta para valer também antes do login.
 */
const THEME_KEY = "iddun.theme.v1";

function isScheme(value: unknown): value is ColorScheme {
  return value === "light" || value === "dark";
}

/** Lê a escolha salva antes da primeira tela, para não piscar o tema. */
export async function loadThemePreference() {
  try {
    const saved = await AsyncStorage.getItem(THEME_KEY);
    setPreferredScheme(isScheme(saved) ? saved : DEFAULT_SCHEME);
  } catch {
    setPreferredScheme(DEFAULT_SCHEME);
  }
}

/** Aplica na hora e grava; se a gravação falhar, a escolha vale na sessão. */
export async function chooseTheme(scheme: ColorScheme) {
  setPreferredScheme(scheme);
  try {
    await AsyncStorage.setItem(THEME_KEY, scheme);
  } catch {
    // Sem espaço ou sem permissão: a tela já mudou; não há o que desfazer.
  }
}
