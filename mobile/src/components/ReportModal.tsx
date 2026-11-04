import React, {
  useState,
} from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  REPORT_CATEGORIES,
  reportContent,
  type ReportCategory,
} from "@/api/feed";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toast";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

/**
 * Denúncia de publicação ou comentário (PR 3; D-SOC-10, DEC-ID-272).
 * Ao enviar, a janela só fecha: sem protocolo nem confirmação para quem
 * denunciou (DEC-ID-275 B). Denúncia não apaga nada.
 */
export type ReportTarget = {
  type: "post" | "comment";
  id: string;
};

export function ReportModal({
  target,
  onClose,
}: {
  target: ReportTarget | null;
  onClose: () => void;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const toast = useToast();
  const [category, setCategory] = useState<ReportCategory | null>(null);
  const [description, setDescription] = useState("");
  const [sending, setSending] = useState(false);

  // Cada abertura começa vazia: os campos são limpos ao fechar.
  const close = () => {
    setCategory(null);
    setDescription("");
    onClose();
  };

  const send = async () => {
    if (!target || !category || sending) {
      return;
    }

    setSending(true);
    try {
      await reportContent(target.type, target.id, category, description);
      close();
    } catch (error) {
      toast.show({
        title: "Não foi possível enviar",
        body: error instanceof Error ? error.message : "Tente novamente.",
        icon: "alert-circle",
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      visible={Boolean(target)}
      transparent
      animationType="fade"
      onRequestClose={close}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.backdrop}
      >
        <View style={styles.sheet} accessibilityViewIsModal>
          <ScrollView keyboardShouldPersistTaps="handled">
            <Text style={styles.title} accessibilityRole="header">
              Denunciar
            </Text>
            <Text style={styles.body}>
              Conte o que está errado. A equipe do IDDUN analisa; nada é apagado automaticamente.
            </Text>

            <View accessibilityRole="radiogroup" style={styles.options}>
              {REPORT_CATEGORIES.map((item) => {
                const selected = item.id === category;
                return (
                  <Pressable
                    key={item.id}
                    accessibilityRole="radio"
                    accessibilityState={{ checked: selected }}
                    onPress={() => setCategory(item.id)}
                    style={({ pressed }) => [
                      styles.option,
                      selected && styles.optionSelected,
                      pressed && styles.pressed,
                    ]}
                  >
                    <Icon
                      name={selected ? "check-circle" : "circle"}
                      size={18}
                      color={selected ? colors.plum : colors.muted}
                    />
                    <Text style={styles.optionText}>{item.label}</Text>
                  </Pressable>
                );
              })}
            </View>

            <TextInput
              value={description}
              onChangeText={setDescription}
              placeholder="Descrição (opcional)"
              placeholderTextColor={colors.muted}
              multiline
              maxLength={1000}
              style={styles.input}
              accessibilityLabel="Descrição da denúncia (opcional)"
            />

            <View style={styles.actions}>
              <Pressable
                accessibilityRole="button"
                onPress={close}
                style={({ pressed }) => [styles.button, pressed && styles.pressed]}
              >
                <Text style={styles.buttonText}>Cancelar</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: !category || sending }}
                disabled={!category || sending}
                onPress={() => void send()}
                style={({ pressed }) => [
                  styles.button,
                  styles.primary,
                  (!category || sending) && styles.disabled,
                  pressed && styles.pressed,
                ]}
              >
                {sending ? (
                  <ActivityIndicator color={colors.onBrandPrimary} />
                ) : (
                  <Text style={[styles.buttonText, styles.primaryText]}>Enviar</Text>
                )}
              </Pressable>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const useStyles = makeStyles((colors) => ({
  backdrop: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: colors.overlayInk,
  },

  sheet: {
    maxHeight: "88%",
    padding: spacing.xl,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    backgroundColor: colors.surfaceSecondary,
  },

  title: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 24,
  },

  body: {
    marginTop: spacing.sm,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 14,
    lineHeight: 20,
  },

  options: {
    marginTop: spacing.lg,
    gap: spacing.xs,
  },

  option: {
    minHeight: touch.minimum,
    paddingHorizontal: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    borderRadius: radius.sm,
  },

  optionSelected: {
    backgroundColor: colors.plumSoft,
  },

  optionText: {
    flex: 1,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 15,
  },

  input: {
    minHeight: 88,
    marginTop: spacing.lg,
    padding: spacing.md,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.glassBorderStrong,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 15,
    textAlignVertical: "top",
  },

  actions: {
    marginTop: spacing.lg,
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: spacing.sm,
  },

  button: {
    minHeight: touch.minimum,
    minWidth: 96,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.glassBorderStrong,
  },

  primary: {
    borderColor: colors.brandPrimary,
    backgroundColor: colors.brandPrimary,
  },

  disabled: {
    opacity: 0.5,
  },

  buttonText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 15,
  },

  primaryText: {
    color: colors.onBrandPrimary,
  },

  pressed: {
    opacity: 0.82,
  },
}));
