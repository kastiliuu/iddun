import { useSyncExternalStore } from "react";
import { useColorScheme as useRNColorScheme } from "react-native";

const subscribeToHydration = () => () => {};

/**
 * Durante SSR usamos um snapshot estável. No cliente,
 * useSyncExternalStore sinaliza que a hidratação já ocorreu
 * sem precisar disparar setState dentro de um effect.
 */
export function useColorScheme() {
  const hasHydrated = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );

  const colorScheme = useRNColorScheme();

  if (hasHydrated) {
    return colorScheme;
  }

  return "light";
}
