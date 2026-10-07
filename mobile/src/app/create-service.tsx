import React from "react";
import {
  Pressable,
  View,
} from "react-native";
import {
  useRouter,
} from "expo-router";

import {
  EmptyState,
} from "@/components/EmptyState";
import {
  Icon,
} from "@/components/Icon";

import {
  makeStyles,
  spacing,
  touch,
  useTheme,
} from "@/theme";

export default function CreateServiceScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Voltar"
          onPress={() => {
            if (router.canGoBack()) {
              router.back();
            } else {
              router.replace(
                "/(tabs)/create",
              );
            }
          }}
          style={styles.backButton}
        >
          <Icon
            name="arrow-left"
            size={20}
            color={colors.onSurface}
          />
        </Pressable>
      </View>

      <EmptyState
        title="Cadastro de serviços em integração"
        description="Criar e editar serviços no app mobile será liberado somente quando o CRUD estiver conectado ao backend real. Nenhum dado local será apresentado como persistido."
        actionLabel="Voltar para Criar"
        onActionPress={() =>
          router.replace(
            "/(tabs)/create",
          )
        }
      />
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

    header: {
      paddingTop: 54,
      paddingHorizontal:
        spacing.lg,
    },

    backButton: {
      width:
        touch.minimum,
      height:
        touch.minimum,
      alignItems:
        "center",
      justifyContent:
        "center",
      borderRadius: 999,
      backgroundColor:
        colors.glassSoft,
      borderWidth: 1,
      borderColor:
        colors.glassBorder,
    },
  }),
);
